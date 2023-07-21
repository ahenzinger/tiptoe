package protocol

import (
  "os"
  "fmt"
  "time"
  "testing"
  "runtime/pprof"
)

import (
  "github.com/henrycg/simplepir/pir"
  "github.com/henrycg/simplepir/matrix"
)

import (
  "github.com/ahenzinger/tiptoe/search/corpus"
  "github.com/ahenzinger/tiptoe/search/utils"
  "github.com/ahenzinger/tiptoe/search/embeddings"
)

const embNumQueries = 20

func testRecoverSingle(s *Server, corp *corpus.Corpus) {
  c := NewClient(false /* use coordinator */)

  var h TiptoeHint
  s.GetHint(true, &h)
  c.Setup(&h)
  logHintSize(&h)

  p := c.embClient.GetP()

  for iter := 0; iter < embNumQueries; iter++ {
    i := utils.RandomIndex(c.NumClusters())
    emb := embeddings.RandomEmbedding(c.params.EmbeddingSlots, (1 << (c.params.SlotBits-1)))
    query := c.QueryEmbeddings(emb, i, false)

    start := time.Now()
    var ans pir.Answer[matrix.Elem64]
    s.GetEmbeddingsAnswer(query, &ans)
    logStats(c.NumDocs(), start, query, &ans)

    dec := c.ReconstructEmbeddings(&ans, i)

    clusterIndex := uint64(corp.ClusterToIndex(uint(i)))
    checkAnswer(dec, clusterIndex, p, emb, corp)
  }
}

func testRecoverCluster(s *Server, corp *corpus.Corpus) {
  c := NewClient(false /* use coordinator */)

  var h TiptoeHint
  s.GetHint(true, &h)
  c.Setup(&h)
  logHintSize(&h)

  p := c.embClient.GetP()

  for iter := 0; iter < embNumQueries; iter++ {
    i := utils.RandomIndex(c.NumClusters())
    emb := embeddings.RandomEmbedding(c.params.EmbeddingSlots, (1 << (c.params.SlotBits-1)))
    query := c.QueryEmbeddings(emb, i, false)

    start := time.Now()
    var ans pir.Answer[matrix.Elem64]
    s.GetEmbeddingsAnswer(query, &ans)
    logStats(c.NumDocs(), start, query, &ans)

    dec := c.ReconstructEmbeddingsWithinCluster(&ans, i)
    checkAnswers(dec, uint(i), p, emb, corp)
  }
}

func testRecoverClusterNetworked(tcp string, useCoordinator bool, corp *corpus.Corpus) {
  c := NewClient(useCoordinator)

  h := c.getHint(false /* keep conn */, tcp)
  c.Setup(h)
  logHintSize(h)

  p := c.embClient.GetP()

  for iter := 0; iter < embNumQueries; iter++ {
    i := utils.RandomIndex(c.NumClusters())
    emb := embeddings.RandomEmbedding(c.params.EmbeddingSlots, (1 << (c.params.SlotBits-1)))
    query := c.QueryEmbeddings(emb, i, false)

    start := time.Now()
    ans := c.getEmbeddingsAnswer(query, false /* keep conn */, tcp)
    logStats(c.NumDocs(), start, query, ans)

    dec := c.ReconstructEmbeddingsWithinCluster(ans, i)

    checkAnswers(dec, uint(i), p, emb, corp)
  }
}

func testRecoverClusterNetworkedDumpState(tcp string, corp *corpus.Corpus) {
  intermfile := "interm/coordinator_state.log"
  fmt.Println("Dumping coordinator state to file")
  DumpStateToFile(&k, intermfile)

  k.hint = nil
  k.Free()

  fmt.Println("Loading coordinator state from file")
  LoadStateFromFile(&k, intermfile)
  k.SetupConns()

  testRecoverClusterNetworked(tcp, true, corp)

  os.Remove(intermfile)
}

func testEmbeddingsServerDumpState(s *Server, corp *corpus.Corpus) {
  s2.Clear() // needed for the test to pass

  intermfile := "interm/server_state.log"
  DumpStateToFile(s, intermfile)
  fmt.Println("Dumping server state to file")

  LoadStateFromFile(&s2, intermfile)
  testRecoverCluster(&s2, corp)
  os.Remove(intermfile)
}

func TestEmbeddingsFakeData(t *testing.T) {
  corp := corpus.ReadEmbeddingsCsv(*medcorpus)
  s.PreprocessEmbeddingsFromCorpus(corp, 25 /* hint size in MB */, conf)
  k.Setup(1, 0, []string{serverTcp}, false, conf)
  
  fmt.Printf("Running embedding queries (over %d-doc fake corpus)\n", corp.GetNumDocs())

  testRecoverSingle(&s, corp)
  testRecoverCluster(&s, corp)
  testEmbeddingsServerDumpState(&s, corp)
  testRecoverClusterNetworked(serverTcp, false, corp)
  testRecoverClusterNetworked(coordinatorTcp, true, corp)
  testRecoverClusterNetworkedDumpState(coordinatorTcp, corp)
}

func TestEmbeddingsRealData(t *testing.T) {
  f, _ := os.Create("emb_test.prof")
  pprof.StartCPUProfile(f)
  defer pprof.StopCPUProfile()

  corp := corpus.ReadEmbeddingsTxt(0, 10, conf)
  s.PreprocessEmbeddingsFromCorpus(corp, 25 /* hint size in MB */, conf)
  k.Setup(1, 0, []string{serverTcp}, false, conf)
  
  fmt.Printf("Running embedding queries (over %d-doc real corpus)\n", corp.GetNumDocs())

  testRecoverSingle(&s, corp)
  testRecoverCluster(&s, corp)
  testEmbeddingsServerDumpState(&s, corp)
  testRecoverClusterNetworked(serverTcp, false, corp)
  testRecoverClusterNetworked(coordinatorTcp, true, corp)
}

func TestEmbeddingsMultipleServersRealData(t *testing.T) {
  numServers := 8
  _, tcps, corp := NewEmbeddingServers(0,
                                       numServers, 
				       10,                // clusters per server
                                       30,                // hint sz
				       false,             // log
				       true,              // want corpus
				       true,              // serve
				       conf)

  for ns := 1; ns <= numServers; ns *= 2 {
    c := corpus.Concat(corp[:ns])
    k.Setup(ns, 0, tcps[:ns], false, conf)
    fmt.Printf("Running embedding queries (over %d-doc real corpus with %d servers)\n", 
               c.GetNumDocs(), ns)
    testRecoverClusterNetworked(coordinatorTcp, true, c)
  }
}
