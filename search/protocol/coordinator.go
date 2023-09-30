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
  "github.com/ahenzinger/underhood/underhood"
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

  embHintServer   *underhood.Server[matrix.Elem64]
  urlHintServer   *underhood.Server[matrix.Elem32]
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

func (c *Coordinator) ApplyHint(ct *underhood.HintQuery, out *UnderhoodAnswer) error {
  if c.hint.ServeEmbeddings {
    if c.embHintServer == nil {
      c.preprocessEmbHint()
    }
    out.EmbAnswer = *c.embHintServer.HintAnswer(ct)

    if c.hint.ServeUrls {
      toDrop := int(c.hint.EmbeddingsHint.Info.Params.N - c.hint.UrlsHint.Info.Params.N)
      *ct = (*ct)[:len(*ct)-toDrop]
    }
  }

  if c.hint.ServeUrls {
    if c.urlHintServer == nil {
      c.preprocessUrlHint()
    }
    out.UrlAnswer = *c.urlHintServer.HintAnswer(ct)
  }

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

func (c *Coordinator) buildHintsLocal(conf *config.Config) {
  // Build embeddings hint
  for i := 0; i < conf.MAX_EMBEDDINGS_SERVERS(); i += BLOCK_SZ {
    fmt.Printf("  on embedding hint %d of %d\n", i, conf.MAX_EMBEDDINGS_SERVERS())
    s, _, _ := NewEmbeddingServers(i, 
                                   i + BLOCK_SZ,
                                   conf.EMBEDDINGS_CLUSTERS_PER_SERVER(),
                                   conf.DEFAULT_EMBEDDINGS_HINT_SZ(),
                                   true, // log
                                   false, // wantCorpus
                                   false, // serve
                                   conf)
    for j := 0; j < BLOCK_SZ; j++ {
      h := s[j].hint
      if i == 0 && j == 0 {
        embeddingsInitInfo(c.hint, h) 
      } else {
        if !embeddingsCheckConsistent(c.hint, h) {
          panic("Embedding hint params are not consistent")
        }
        embeddingsMergeInfo(c.hint, h)
      }
    }
    runtime.GC()
  }

  // Build URL hint
  s, _, _ := NewUrlServers(conf.MAX_URL_SERVERS(),
                           conf.URL_CLUSTERS_PER_SERVER(),
                           config.DEFAULT_URL_HINT_SZ(),
                           true, // log
                           false, // wantCorpus
                           false, // serve
                           conf)
  h := s[0].hint
  urlsInitInfo(c.hint, h)

  for i := 1; i < conf.MAX_URL_SERVERS(); i++ {
    fmt.Printf("  on url hint %d of %d\n", i, conf.MAX_URL_SERVERS())
    h := s[i].hint
    if !urlsCheckConsistent(c.hint, h) {
      panic("URL hint params are not consistent")
    }
    urlsMergeInfo(c.hint, h)
    runtime.GC()
  }
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

func (c *Coordinator) preprocessEmbHint() {
  // Decompose hint
  c.embHintServer = underhood.NewServerHintOnly(&c.hint.EmbeddingsHint.Hint)

  // Drop hint contents that shouldn't be sent back
  rows := c.hint.EmbeddingsHint.Hint.Rows()
  c.hint.EmbeddingsHint.Hint.DropLastrows(rows)
}

func (c *Coordinator) preprocessUrlHint() {
  // Decompose hint
  c.urlHintServer = underhood.NewServerHintOnly(&c.hint.UrlsHint.Hint)

  // Drop hint contents that shouldn't be sent back
  rows := c.hint.UrlsHint.Hint.Rows()
  c.hint.UrlsHint.Hint.DropLastrows(rows)
}

func (c *Coordinator) preprocessHint() {
  if c.hint.ServeEmbeddings {
    c.preprocessEmbHint()
  }

  if c.hint.ServeUrls {
    c.preprocessUrlHint()
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

  c.preprocessHint()
}

func LocalSetupCoordinator(conf *config.Config) {
  fmt.Println("Setting up coordinator")

  // Init state
  c := coordinatorInit()
  c.hint = new(TiptoeHint)
  c.numEmbServers = conf.MAX_EMBEDDINGS_SERVERS()
  c.hint.ServeEmbeddings = (c.numEmbServers > 0)

  c.numUrlServers = conf.MAX_URL_SERVERS()
  c.hint.ServeUrls = (c.numUrlServers > 0)

  // Gather and merge hints from servers
  fmt.Println("  0. Gathering hints -- locally")
  c.buildHintsLocal(conf)

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

  // Write state to file
  logfile := conf.CoordinatorLog(c.numEmbServers, c.numUrlServers)
  DumpStateToFile(c, logfile)
}

func RunCoordinator(numEmbServers, numUrlServers, port int,
                    addrs []string, log bool, conf *config.Config) {
  k := coordinatorInit()
  k.Setup(numEmbServers, numUrlServers, addrs, log, conf)
  fmt.Println("Ready to start answering queries")
  k.Serve(port)
}

func (c *Coordinator) Serve(port int) {
  rs := rpc.NewServer()
  rs.Register(c)
  utils.ListenAndServeTLS(rs, port)
}

func coordinatorInit() *Coordinator {
  return new(Coordinator)
}

func (c *Coordinator) Free() {
  for _, conn := range c.embServerConns {
    conn.Close()
  }

  for _, conn := range c.urlServerConns {
    conn.Close()
  }

  if c.embHintServer != nil {
    c.embHintServer.Free()
  }

  if c.urlHintServer != nil {
    c.urlHintServer.Free()
  }
}
