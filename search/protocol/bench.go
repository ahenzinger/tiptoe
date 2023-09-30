package protocol

import (
  "fmt"
  "sync"
  "time"
  "net/rpc"
)

import (
  "github.com/henrycg/simplepir/pir"
  "github.com/henrycg/simplepir/matrix"
  "github.com/ahenzinger/underhood/underhood"
)

import (
  "github.com/ahenzinger/tiptoe/search/utils"
  "github.com/ahenzinger/tiptoe/search/config"
  "github.com/ahenzinger/tiptoe/search/embeddings"
)

type ExperimentType int
const (
  EMBEDDINGS ExperimentType = 0
  URLS       ExperimentType = 1
  OFFLINE    ExperimentType = 2
)

func BenchLatency(numQueries int, coordinatorAddr, logfile string, conf *config.Config) {
  c := NewClient(true /* coordinator */)
  h := c.getHint(true /* keep conn */, coordinatorAddr)
  c.Setup(h)
  //hintSz := logHintSize(*h)

  in, out := embeddings.SetupEmbeddingProcess(c.NumClusters(), conf)
  perf := make([]Perf, numQueries)

  txtQueries := make([]string, numQueries)
  txtQueries[0] = "what test are relvant for heart screenings"
  txtQueries[1] = "what is the ige antibody"
  txtQueries[2] = "foodborne trematodiases symptoms"

  for iter := 3; iter < numQueries; iter++ {
    txtQueries[iter] = utils.RandString(10)
  }

  for iter := 0; iter < numQueries; iter++ {
    fmt.Printf("%d.\n", iter)

    p := c.preprocessRound(coordinatorAddr, true /* verbose */, true /* keep conn */)
    perf[iter] = c.runRound(p, in, out, txtQueries[iter], coordinatorAddr, true /* verbose */, true /* keep conn */)
  }

  numEmbServers := len(h.EmbeddingsHint.Seeds)
  numUrlServers := len(h.UrlsHint.Seeds)
  initCsv(logfile)
  writeLatencyCsv(logfile, perf, &c.params, 0, numEmbServers, numUrlServers)

  c.closeConn()
  in.Close()
  out.Close()
}

func benchTput[T QueryType](coordinatorAddr, logfile string,
			    experiment ExperimentType,
                            buildQuery func(*Client) *T,
                            sendQuery func(*T, *rpc.Client) ) {
  c := NewClient(true /* coordinator */)
  h := c.getHint(false /* keep conn */, coordinatorAddr)
  hintSz := logHintSize(h)
  c.Setup(h)

  numQueries := 50

  fmt.Println("Set up first client")

  queries := make([]*T, numQueries)
  for i := 0; i < numQueries; i++ {
    queries[i] = buildQuery(c)
  }

  nc := make([]int, 0)
  perf := make([]Perf, 0)
  for numClients := 1; numClients < 20; numClients += 2 {
    var p Perf

    timeUp := false
    var timeMu sync.Mutex

    queriesRead := 0
    var readMu sync.Mutex

    queriesAnswered := 0
    var answeredMu sync.Mutex

    start := time.Now()
    for i := 0; i < numClients; i++ {
      go func(i int) {
        for ; ; {
          readMu.Lock()
          at := (queriesRead % numQueries)
          queriesRead++
          readMu.Unlock()

          query := queries[at]
          rpcClient := utils.DialTLS(coordinatorAddr)
          sendQuery(query, rpcClient)
          rpcClient.Close()

          answeredMu.Lock()
          queriesAnswered += 1
          answeredMu.Unlock()

          timeMu.Lock()
          if timeUp {
            timeMu.Unlock()
            return
          }
          timeMu.Unlock()
        }
      }(i)
    }

    time.Sleep(60000 * time.Millisecond)

    answeredMu.Lock()
    elapsed := time.Since(start)
    tput := float64(queriesAnswered) / elapsed.Seconds()
    answeredMu.Unlock()

    timeMu.Lock()
    timeUp = true
    timeMu.Unlock()

    nc = append(nc, numClients)
    fmt.Printf("  %d clients: %d queries answered in %f seconds\n",
               numClients, queriesAnswered, elapsed.Seconds())
    fmt.Printf("  Measured tput: %f queries/second\n", tput)

    switch experiment {
    case EMBEDDINGS:
      p.tput1 = tput
    case URLS:
      p.tput2 = tput
    case OFFLINE:
      p.tputOffline = tput
    }

    perf = append(perf, p)
    time.Sleep(60000 * time.Millisecond) // To wait for stragglers...
  }

  numEmbServers := len(h.EmbeddingsHint.Seeds)
  numUrlServers := len(h.UrlsHint.Seeds)
  initCsv(logfile)
  writeTputCsv(logfile, nc, perf, &c.params, hintSz, numEmbServers, numUrlServers)
}

func BenchTputEmbed(coordinatorAddr, logfile string) {
  buildQuery := func (c *Client) *pir.Query[matrix.Elem64] {
    emb := embeddings.RandomEmbedding(c.params.EmbeddingSlots, (1 << (c.params.SlotBits-1)))
    c.embClient.HintQuery()
    c.embClient.PreprocessQueryLHE()
    return c.QueryEmbeddings(emb, 0) // Doesn't matter which index recovering...
  }

  sendQuery := func (query *pir.Query[matrix.Elem64], rpcClient *rpc.Client) {
    reply := pir.Answer[matrix.Elem64]{}
    utils.CallTLS(rpcClient, "Coordinator.GetEmbeddingsAnswer", query, &reply)
  }

  benchTput(coordinatorAddr, logfile, EMBEDDINGS, buildQuery, sendQuery)
}

func BenchTputUrl(coordinatorAddr, logfile string) {
  buildQuery := func (c *Client) *pir.Query[matrix.Elem32] {
    c.urlClient.HintQuery()
    c.urlClient.PreprocessQuery()
    q, _ := c.QueryUrls(0, 0) // Doesn't matter which index recovering...
    return q
  }

  sendQuery := func (query *pir.Query[matrix.Elem32], rpcClient *rpc.Client) {
    reply := pir.Answer[matrix.Elem32]{}
    utils.CallTLS(rpcClient, "Coordinator.GetUrlsAnswer", query, &reply)
  }

  benchTput(coordinatorAddr, logfile, URLS, buildQuery, sendQuery)
}

func BenchTputOffline(coordinatorAddr, logfile string) {
  buildQuery := func (c *Client) *underhood.HintQuery {
    return c.PreprocessQuery()
  }

  sendQuery := func (query *underhood.HintQuery, rpcClient *rpc.Client) {
    reply := UnderhoodAnswer{}
    utils.CallTLS(rpcClient, "Coordinator.ApplyHint", query, &reply)
  }

  benchTput(coordinatorAddr, logfile, OFFLINE, buildQuery, sendQuery)
}
