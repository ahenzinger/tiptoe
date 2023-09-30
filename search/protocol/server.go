package protocol

import (
  "fmt"
  "net/rpc"
)

import (
  "github.com/henrycg/simplepir/pir"
  "github.com/henrycg/simplepir/rand"
  "github.com/henrycg/simplepir/matrix"
)

import (
  "github.com/ahenzinger/tiptoe/search/corpus"
  "github.com/ahenzinger/tiptoe/search/database"
  "github.com/ahenzinger/tiptoe/search/config"
  "github.com/ahenzinger/tiptoe/search/utils"
)

// Number of servers to launch at once
const BLOCK_SZ = 10

type TiptoeHint struct {
  CParams               corpus.Params

  ServeEmbeddings       bool
  EmbeddingsHint        utils.PIR_hint[matrix.Elem64]
  EmbeddingsIndexMap    database.ClusterMap

  ServeUrls             bool
  UrlsHint              utils.PIR_hint[matrix.Elem32]
  UrlsIndexMap          database.SubclusterMap
}

type Server struct {
  hint                  *TiptoeHint
  embeddingsServer      *pir.Server[matrix.Elem64]
  urlsServer            *pir.Server[matrix.Elem32]
}

func (s *Server) PreprocessEmbeddingsFromCorpus(c *corpus.Corpus, hintSz uint64, conf *config.Config) {
  embeddings_seed := rand.RandomPRGKey()
  s.preprocessEmbeddingsSeeded(c, embeddings_seed, hintSz, conf)
}

func (s *Server) preprocessEmbeddingsSeeded(c *corpus.Corpus,
                                            seed *rand.PRGKey,
					    hintSz uint64,
				            conf *config.Config) {
  fmt.Printf("Preprocessing a corpus of %d embeddings of length %d\n",
              c.GetNumDocs(), c.GetEmbeddingSlots())

  db, indexMap := database.BuildEmbeddingsDatabase(c, seed, hintSz, conf)
  s.embeddingsServer = pir.NewServerSeed(db, seed)

  s.hint = new(TiptoeHint)
  s.hint.ServeEmbeddings = true
  s.hint.CParams = c.GetParams()

  s.hint.EmbeddingsHint.Hint = *s.embeddingsServer.Hint()
  s.hint.EmbeddingsHint.Info = *s.embeddingsServer.DBInfo()
  s.hint.EmbeddingsHint.Seeds = []rand.PRGKey{ *seed }
  s.hint.EmbeddingsHint.Offsets = []uint64{ s.hint.EmbeddingsHint.Info.M }
  s.hint.EmbeddingsIndexMap = indexMap

  // THIS CHECK DOES NOT MAKE SENSE FOR IMAGE DATASET, BECAUSE VECTORS ARE NORMALIZED
  max_inner_prod := 2 * (1 << (2*c.GetSlotBits()-2)) * c.GetEmbeddingSlots()
  if (!conf.IMAGE_SEARCH()) && (s.embeddingsServer.Params().P < max_inner_prod) {
    fmt.Printf("%d < %d\n", s.embeddingsServer.Params().P, max_inner_prod)
    panic("Parameters not supported. Inner products may wrap around.")
  }

  fmt.Println("    done")
}

func (s *Server) PreprocessUrlsFromCorpus(c *corpus.Corpus, hintSz uint64) {
  urls_seed := rand.RandomPRGKey()
  s.preprocessUrlsSeeded(c, urls_seed, hintSz)
}

func (s *Server) preprocessUrlsSeeded(c *corpus.Corpus,
                                      seed *rand.PRGKey,
				      hintSz uint64) {
  fmt.Printf("Preprocessing a corpus of %d urls in chunks of length <= %d\n",
             c.GetNumDocs(), c.GetUrlBytes())

  db, indexMap := database.BuildUrlsDatabase(c, seed, hintSz)
  s.urlsServer = pir.NewServerSeed(db, seed)

  s.hint = new(TiptoeHint)
  s.hint.ServeUrls = true
  s.hint.CParams = c.GetParams()

  s.hint.UrlsHint.Hint = *s.urlsServer.Hint()
  s.hint.UrlsHint.Info = *s.urlsServer.DBInfo()
  s.hint.UrlsHint.Seeds = []rand.PRGKey{ *seed }
  s.hint.UrlsHint.Offsets = []uint64{ s.hint.UrlsHint.Info.M }
  s.hint.UrlsIndexMap = indexMap

  fmt.Println("    done")
}

// Note: need to keep full hint contents here!!
func (s *Server) GetHint(request bool, hint *TiptoeHint) error {
  *hint = *s.hint 
  return nil
}

func (s *Server) GetEmbeddingsAnswer(query *pir.Query[matrix.Elem64],
                                     ans *pir.Answer[matrix.Elem64]) error {
  *ans = *s.embeddingsServer.Answer(query)
  return nil
}

func (s *Server) GetUrlsAnswer(query *pir.Query[matrix.Elem32],
                               ans *pir.Answer[matrix.Elem32]) error {
  *ans = *s.urlsServer.Answer(query)
  return nil
}

func NewEmbeddingServers(serversStart, serversEnd, clustersPerServer int,
                         hintSz uint64,
			 log, wantCorpus, serve bool,
		         conf *config.Config) ([]*Server, []string, []*corpus.Corpus) {
  fmt.Println(" ... Reading corpus")
  servers := make([]*Server, 0, serversEnd - serversStart)
  corpuses := make([]*corpus.Corpus, 0, serversEnd - serversStart)
  var addrs []string

  serverSetup := func(s *Server, c *corpus.Corpus) {
    s.PreprocessEmbeddingsFromCorpus(c, hintSz, conf)
  }

  for i := serversStart; i < serversEnd; i += BLOCK_SZ {
    numToLaunch := BLOCK_SZ
    if i + numToLaunch >= serversEnd {
      numToLaunch = serversEnd - i
    }

    corpusSetup := func(j int) *corpus.Corpus {
      return corpus.ReadEmbeddingsTxt(clustersPerServer * (i + j),
			              clustersPerServer * (i + j + 1),
			              conf)
    }

    if !log {
      s, c := launchServers(numToLaunch, corpusSetup, serverSetup)
      servers = append(servers, s...)
      corpuses = append(corpuses, c...)
    } else {
      logs := make([]string, numToLaunch)
      for j := 0; j < numToLaunch; j++ {
        logs[j] = conf.EmbeddingServerLog(i + j)
      }

      s, c := launchServersFromLogs(logs, corpusSetup, serverSetup, wantCorpus)
      servers = append(servers, s...)
      corpuses = append(corpuses, c...)
    }
  }

  if serve {
    addrs = Serve(servers, utils.EmbServerPortStart)
  }

  return servers, addrs, corpuses
}

func NewUrlServers(numServers, clustersPerServer int,
                   hintSz uint64,
		   log, wantCorpus, serve bool,
	           conf *config.Config) ([]*Server, []string, []*corpus.Corpus) {
  var servers []*Server
  var addrs []string
  var corpuses []*corpus.Corpus

  fmt.Println(" ... Reading URL corpus")
  corpusSetup := func(i int) *corpus.Corpus {
    from := clustersPerServer * i
    to := from + clustersPerServer
    return corpus.ReadUrlsTxt(from, to, conf)
  }

  serverSetup := func(s *Server, c *corpus.Corpus) {
    s.PreprocessUrlsFromCorpus(c, hintSz)
  }

  if !log {
    servers, corpuses = launchServers(numServers, corpusSetup, serverSetup)
  } else {
    logs := make([]string, numServers)
    for i := 0; i < numServers; i++ {
      logs[i] = conf.UrlServerLog(i)
    }
    servers, corpuses = launchServersFromLogs(logs, corpusSetup, serverSetup, wantCorpus)
  }

  if serve {
    addrs = Serve(servers, utils.UrlServerPortStart)
  }

  return servers, addrs, corpuses
}

func launchServers(num int,
                   corpusSetup func(int) *corpus.Corpus,
                   serverSetup func(*Server, *corpus.Corpus)) ([]*Server, []*corpus.Corpus) {
  servers := make([]*Server, num)
  corpuses := make([]*corpus.Corpus, num)
  ch := make(chan bool)

  for i := 0; i < num; i++ {
    go func(i int) {
      servers[i] = serverInit() 
      corpuses[i] = corpusSetup(i)
      serverSetup(servers[i], corpuses[i])
      ch <- true
    }(i)
  }

  utils.ReadFromChannel(ch, num, true)

  return servers, corpuses
}

func launchServersFromLogs(logs []string,
                           corpusSetup func(int) *corpus.Corpus,
                           serverSetup func(*Server, *corpus.Corpus),
			   wantCorpus bool) ([]*Server, []*corpus.Corpus) {
  if len(logs) == 0 {
    panic("Empty input")
  }

  fmt.Println("In LaunchServersFromLogs")
  servers := make([]*Server, len(logs))
  corpuses := make([]*corpus.Corpus, len(logs))

  ch := make(chan bool)
  numLaunched := 0
  for i := 0; i < len(logs); i++ {
    if utils.FileExists(logs[i]) {
      fmt.Printf("File %s exists ...\n", logs[i])
      // generate corpus
      if wantCorpus {
        go func(i int) {
          corpuses[i] = corpusSetup(i)
          ch <- true
        }(i)
	numLaunched += 1
      }

      // in parallel, set up server
      go func(i int) {
	servers[i] = serverInit() 
        LoadStateFromFile(servers[i], logs[i])
        ch <- true
      }(i)
      numLaunched += 1
    } else {
      // generate corpus, set up server, and write to file in sequence
      go func(i int) {
	servers[i] = serverInit() 
        corpuses[i] = corpusSetup(i)
	serverSetup(servers[i], corpuses[i])
	DumpStateToFile(servers[i], logs[i])
	ch <- true
      }(i)
      numLaunched += 1
    }
  }

  utils.ReadFromChannel(ch, numLaunched, true)

  return servers, corpuses
}

func NewServerFromFile(file string) *Server {
  s := serverInit() 
  LoadStateFromFile(s, file)
  return s
}

func NewServerFromFileWithoutHint(file string) *Server {
  s := serverInit() 
  LoadServerFromFileWithoutHint(s, file)
  return s
}

func (s *Server) Serve(port int) {
  rs := rpc.NewServer()
  rs.Register(s)
  utils.ListenAndServeTCP(rs, port)
}

func Serve(servers []*Server, portOffset int) []string {
  addrs := make([]string, len(servers))

  for i := 0; i < len(servers); i++ {
    addrs[i] = utils.LocalAddr(portOffset + i)
    go servers[i].Serve(portOffset + i)
  }

  return addrs
}

func serverInit() *Server {
  s := new(Server)
  return s
}

func (s *Server) Clear() {
  s.embeddingsServer = nil
  s.urlsServer = nil
  s.hint = nil
}
