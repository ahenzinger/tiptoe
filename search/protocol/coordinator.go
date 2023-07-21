package protocol

import (
  "fmt"
  "runtime"
  "net/rpc"
)

import (
  "github.com/henrycg/simplepir/pir"
  "github.com/henrycg/simplepir/lwe"
  "github.com/henrycg/simplepir/matrix"
)

import (
  "github.com/ahenzinger/tiptoe/search/config"
  "github.com/ahenzinger/tiptoe/search/database"
  "github.com/ahenzinger/tiptoe/search/utils"
)

type Coordinator struct {
  numEmbServers    int
  embServerAddrs   []string
  embServerConns   []*rpc.Client

  numUrlServers    int
  urlServerAddrs   []string
  urlServerConns   []*rpc.Client

  hint             *TiptoeHint
}

func callServer[T matrix.Elem](conn *rpc.Client,
                               query *pir.Query[T],
			       ans *pir.Answer[T],
                               rpcName string) {
  utils.CallTCP(conn, rpcName, query, ans)
}

func callServerAlloc[T matrix.Elem](conn *rpc.Client, 
                                    query *pir.Query[T], 
			            rpcName string) *pir.Answer[T] {
  ans := new(pir.Answer[T])
  utils.CallTCP(conn, rpcName, query, ans)
  return ans
}

func callServers[T matrix.Elem](query *pir.Query[T], ans *pir.Answer[T], rpcName string,
                                serverConns []*rpc.Client, hint *utils.PIR_hint[T]) {
  numServers := len(serverConns)

  // Contact each of the cluster servers in parallel
  ch := make(chan *pir.Answer[T])
  at := hint.Offsets[0]

  for i := 1; i < numServers; i++ {
    offset := hint.Offsets[i]

    go func(at, offset uint64, conn *rpc.Client) {
      q := query.SelectRows(at, offset, hint.Info.Squishing)
      ch <- callServerAlloc(conn, q, rpcName) 
    } (at, offset, serverConns[i])

    at += offset
  }

  callServer(serverConns[0], 
             query.SelectRows(0, hint.Offsets[0], hint.Info.Squishing), 
	     ans, 
	     rpcName)

  // Add responses
  for i := 1; i < numServers; i++ {
    a := <- ch
    ans.Answer.AddWithMismatch(a.Answer)
  }
}

func (c *Coordinator) GetHint(request bool, h *TiptoeHint) error {
  *h = *c.hint 
  return nil
}

func (c *Coordinator) GetEmbeddingsAnswer(query *pir.Query[matrix.Elem64], 
                                          ans *pir.Answer[matrix.Elem64]) error {
  if c.numEmbServers == 0 {
    panic("Coordinator does not know of any cluster servers.")
  }

  callServers(query, ans, "Server.GetEmbeddingsAnswer", c.embServerConns, &c.hint.EmbeddingsHint)

  return nil
}

func (c *Coordinator) GetUrlsAnswer(query *pir.Query[matrix.Elem32], 
                                    ans *pir.Answer[matrix.Elem32]) error {
  if c.numUrlServers == 0 {
    panic("Coordinator does not know of any URL servers")
  }

  callServers(query, ans, "Server.GetUrlsAnswer", c.urlServerConns, &c.hint.UrlsHint)

  return nil
}

func (c *Coordinator) SetupConns() {
  c.embServerConns = make([]*rpc.Client, c.numEmbServers)
  c.urlServerConns = make([]*rpc.Client, c.numUrlServers)

  for i := 0; i < c.numEmbServers; i++ {
    c.embServerConns[i] = utils.DialTCP(c.embServerAddrs[i])
  }

  for i := 0; i < c.numUrlServers; i++ {
    c.urlServerConns[i] = utils.DialTCP(c.urlServerAddrs[i])
  }
}

func (c *Coordinator) fetchHints(addrs []string, 
                                 initInfo func(*TiptoeHint, *TiptoeHint),
				 checkConsistent func(*TiptoeHint, *TiptoeHint) bool,
			         mergeInfo func(*TiptoeHint, *TiptoeHint)) []*rpc.Client {
  if len(addrs) == 0 {
    return nil
  }

  conns := make([]*rpc.Client, len(addrs))
  conns[0] = utils.DialTCP(addrs[0])

  h := TiptoeHint{}
  utils.CallTCP(conns[0], "Server.GetHint", true, &h)
  initInfo(c.hint, &h) 

  for i := 1; i < len(addrs); i++ {
    h := TiptoeHint{}
    conns[i] = utils.DialTCP(addrs[i])
    utils.CallTCP(conns[i], "Server.GetHint", true, &h)

    if !checkConsistent(c.hint, &h) {
      panic("Hint params are not consistent")
    }
    mergeInfo(c.hint, &h)
    runtime.GC()
  }

  return conns
}

func embeddingsInitInfo(nh *TiptoeHint, h *TiptoeHint) {
  nh.CParams.NumDocs = h.CParams.NumDocs
  nh.CParams.EmbeddingSlots = h.CParams.EmbeddingSlots
  nh.CParams.SlotBits = h.CParams.SlotBits
  nh.EmbeddingsHint = h.EmbeddingsHint
  nh.EmbeddingsIndexMap = h.EmbeddingsIndexMap
}

func embeddingsCheckConsistent(nh *TiptoeHint, h *TiptoeHint) bool {
  if (nh.CParams.EmbeddingSlots != h.CParams.EmbeddingSlots) ||
     (nh.CParams.SlotBits != h.CParams.SlotBits) {
    return false
  }
  return true
}

func embeddingsMergeInfo(nh *TiptoeHint, h *TiptoeHint) {
  nh.CParams.NumDocs += h.CParams.NumDocs
  database.MergeClusterMap(nh.EmbeddingsIndexMap, h.EmbeddingsIndexMap, 
                           nh.EmbeddingsHint.Info.M, h.EmbeddingsHint.Info.M)
  utils.MergeHints(&nh.EmbeddingsHint, h.EmbeddingsHint)
}

func urlsInitInfo(nh *TiptoeHint, h *TiptoeHint) {
  if !nh.ServeEmbeddings {
    nh.CParams.NumDocs += h.CParams.NumDocs
  }
  nh.CParams.UrlBytes = h.CParams.UrlBytes
  nh.CParams.CompressUrl = h.CParams.CompressUrl
  nh.UrlsHint = h.UrlsHint
  nh.UrlsIndexMap = h.UrlsIndexMap
}

func urlsCheckConsistent(nh *TiptoeHint, h *TiptoeHint) bool {
  if (nh.CParams.CompressUrl != h.CParams.CompressUrl) {
    return false
  }
  return true
}

func urlsMergeInfo(nh *TiptoeHint, h *TiptoeHint) {
  if !nh.ServeEmbeddings {
    nh.CParams.NumDocs += h.CParams.NumDocs
  }

  database.MergeSubclusterMap(nh.UrlsIndexMap, h.UrlsIndexMap, 
                              nh.UrlsHint.Info.M, h.UrlsHint.Info.M)
  utils.MergeHints(&nh.UrlsHint, h.UrlsHint)

  if h.CParams.UrlBytes > nh.CParams.UrlBytes {
    nh.CParams.UrlBytes = h.CParams.UrlBytes
  }
}

func (c *Coordinator) setup(numEmbServers, numUrlServers int, addrs []string) {
  // Init state
  c.hint = new(TiptoeHint)
  c.numEmbServers = numEmbServers
  c.embServerAddrs = addrs[:numEmbServers]
  c.hint.ServeEmbeddings = (numEmbServers > 0)

  c.numUrlServers = numUrlServers
  c.urlServerAddrs = addrs[numEmbServers:]
  c.hint.ServeUrls = (numUrlServers > 0)

  // Gather and merge hints from servers
  fmt.Println("  0. Gathering hints")
  c.embServerConns = c.fetchHints(c.embServerAddrs, 
                                  embeddingsInitInfo,
				  embeddingsCheckConsistent,
		  	          embeddingsMergeInfo)

  c.urlServerConns = c.fetchHints(c.urlServerAddrs, 
                                  urlsInitInfo,
				  urlsCheckConsistent,
		                  urlsMergeInfo)

  // Check that LWE params are safe
  if c.hint.ServeEmbeddings && !lwe.CheckParams(c.hint.EmbeddingsHint.Info.Params.Logq,
                                                c.hint.EmbeddingsHint.Info.M,
		                                c.hint.EmbeddingsHint.Info.Params.P) {
    panic("LWE params used for embeddings are bad.")
  }

  if c.hint.ServeUrls && !lwe.CheckParams(c.hint.UrlsHint.Info.Params.Logq,
                                          c.hint.UrlsHint.Info.M,
		                          c.hint.UrlsHint.Info.Params.P) {
    panic("LWE params used for URLs are bad.")
  }
}

func (c *Coordinator) Setup(numEmbServers, numUrlServers int, 
			    addrs []string, 
			    log bool,
		            conf *config.Config) {
  if len(addrs) != numEmbServers + numUrlServers {
    panic("Bad input")
  }
  fmt.Println("Setting up coordinator")

  logfile := conf.CoordinatorLog(numEmbServers, numUrlServers)
 
  if log && utils.FileExists(logfile) {
    LoadStateFromFile(c, logfile)
    c.embServerAddrs = addrs[:numEmbServers]
    c.urlServerAddrs = addrs[numEmbServers:]
    c.SetupConns()
  } else {
    c.setup(numEmbServers, numUrlServers, addrs)
    if log {
      DumpStateToFile(c, logfile)
    }
  }
}

func RunCoordinator(numEmbServers, numUrlServers, port int, 
                    addrs []string, log bool, conf *config.Config) {
  k := new(Coordinator)
  k.Setup(numEmbServers, numUrlServers, addrs, log, conf)
  fmt.Println("Ready to start answering queries")
  k.Serve(port)
}

func (c *Coordinator) Serve(port int) {
  rs := rpc.NewServer()
  rs.Register(c)
  utils.ListenAndServeTLS(rs, port)
}

func (c *Coordinator) Free() {
  for _, conn := range c.embServerConns {
    conn.Close()
  }

  for _, conn := range c.urlServerConns {
    conn.Close()
  }
}
