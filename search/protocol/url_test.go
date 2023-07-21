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
  "github.com/ahenzinger/tiptoe/search/utils"
  "github.com/ahenzinger/tiptoe/search/corpus"
  "github.com/ahenzinger/tiptoe/search/config"
)

const urlNumQueries = 2

func testRecoverUrl(s *Server, corp *corpus.Corpus) {
  c := NewClient(false /* use coordinator */)

  var h TiptoeHint
  s.GetHint(true, &h)
  c.Setup(&h)
  logHintSize(&h)

  for iter := 0; iter < urlNumQueries; iter++ {
    i := utils.RandomIndex(c.NumClusters())
    chunks, ok := c.urlMap[uint(i)]

    if !ok {
      fmt.Printf("Key %d does not exist in map of length %d\n", i, c.NumClusters())
      panic("Should not happen")
    }

    numChunks := len(chunks)
    if numChunks == 0 {
      panic("Cluster is empty")
    }

    answerUrl := corp.GetUrlsInCluster(i)
    recoveredUrl := ""
    for ch := 0; ch < numChunks; ch++ {
      fakeIndex := c.urlMap.FakeIndexInSubcluster(i, uint64(ch))
      q, _ := c.QueryUrls(i, fakeIndex, false)

      var ans pir.Answer[matrix.Elem32]
      start := time.Now()
      s.GetUrlsAnswer(q, &ans)
      logStats(c.NumDocs(), start, q, &ans)

      recovered := c.ReconstructUrls(&ans, i, fakeIndex)
      checkSubclusterSize(recovered, i, ch, corp)

      recoveredUrl += recovered
    }

    if recoveredUrl != answerUrl {
      fmt.Printf("%s != %s\n", recoveredUrl, answerUrl)
      panic("Bad answer")
    }
  }
}

func testRecoverUrlNetworked(tcp string, useCoordinator bool, corp *corpus.Corpus) {
  c := NewClient(useCoordinator)

  h := c.getHint(false /* keep conn */, tcp)
  c.Setup(h)
  logHintSize(h)

  for iter := 0; iter < urlNumQueries; iter++ {
    i := utils.RandomIndex(c.NumClusters())
    _, ok := c.urlMap[uint(i)]

    if !ok {
      fmt.Printf("Key %d does not exist in map of length %d\n", i, c.NumClusters())
      panic("Should not happen")
    }

    numChunks := len(c.urlMap[uint(i)])

    if numChunks == 0 {
      panic("Cluster is empty")
    }

    answerUrl := corp.GetUrlsInCluster(i)
    recoveredUrl := ""
    for ch := 0; ch < numChunks; ch++ {
      fakeIndex := c.urlMap.FakeIndexInSubcluster(i, uint64(ch))
      q, _ := c.QueryUrls(i, fakeIndex, false)

      start := time.Now()
      ans := c.getUrlsAnswer(q, false /* keep conn */, tcp)
      logStats(c.NumDocs(), start, q, ans)

      recovered := c.ReconstructUrls(ans, i, fakeIndex)
      checkSubclusterSize(recovered, i, ch, corp)
       
      recoveredUrl += recovered
    }

    if recoveredUrl != answerUrl {
      fmt.Printf("%s != %s\n", recoveredUrl, answerUrl)
      panic("Bad answer")
    }
  }
}

func testUrlServerDumpState(s *Server, corp *corpus.Corpus) {
  s2.Clear() // needed for the test to pass

  intermfile := "interm/server_state.log"
  DumpStateToFile(s, intermfile)
  LoadStateFromFile(&s2, intermfile)
  testRecoverUrl(&s2, corp)

  os.Remove(intermfile)
}

func TestUrlFakeData(t *testing.T) {
  corp := corpus.ReadUrlsCsv(*medcorpus, true)
  s.PreprocessUrlsFromCorpus(corp, 5 /* hint size in MB */)
  k.Setup(0, 1, []string{serverTcp}, false, conf)

  fmt.Printf("Running URL queries (over %d-doc fake corpus)\n", corp.GetNumDocs())

  testRecoverUrl(&s, corp)
  testUrlServerDumpState(&s, corp)
  testRecoverUrlNetworked(serverTcp, false, corp)
  testRecoverUrlNetworked(coordinatorTcp, true, corp)
}

func TestUrlRealData(t *testing.T) {
  f, _ := os.Create("url_test.prof")
  pprof.StartCPUProfile(f)
  defer pprof.StopCPUProfile()

  corp := corpus.ReadUrlsTxt(0, 300, conf)
  s.PreprocessUrlsFromCorpus(corp, 20 /* hint size in MB */)
  k.Setup(0, 1, []string{serverTcp}, false, conf)

  fmt.Printf("Running URL queries (over %d-doc real corpus)\n",
             corp.GetNumDocs())

  testRecoverUrl(&s, corp)
  testUrlServerDumpState(&s, corp)
  testRecoverUrlNetworked(serverTcp, false, corp)
  testRecoverUrlNetworked(coordinatorTcp, true, corp)
}

func TestUrlMultipleServersRealData(t *testing.T) {
  numServers := conf.MAX_URL_SERVERS()
  _, tcps, corp := NewUrlServers(numServers, 
                                 100, // clusters per server
				 config.DEFAULT_URL_HINT_SZ(), 
				 false, // log
				 true,  // want corpus
				 true,  // serve
				 conf)

  for ns := 1; ns <= numServers; ns *= 2 {
    fmt.Printf("Working with %d servers.\n", ns)
    c := corpus.Concat(corp[:ns])
    k.Setup(0, ns, tcps[:ns], false, conf)
    fmt.Printf("Running URL queries (over %d-doc real corpus with %d servers)\n",
               c.GetNumDocs(), ns)
    testRecoverUrlNetworked(coordinatorTcp, true, c)
  }
}
