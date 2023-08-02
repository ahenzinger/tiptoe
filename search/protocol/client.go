package protocol

import (
  "fmt"
  "io"
  "os"
  "log"
  "encoding/gob"
  "time"
  "strings"
  "net/rpc"
  "encoding/json"
)

import (
  "github.com/henrycg/simplepir/pir"
  "github.com/henrycg/simplepir/matrix"
)

import (
  "github.com/ahenzinger/tiptoe/search/utils"
  "github.com/ahenzinger/tiptoe/search/corpus"
  "github.com/ahenzinger/tiptoe/search/config"
  "github.com/ahenzinger/tiptoe/search/embeddings"
  "github.com/ahenzinger/tiptoe/search/database"
)

import (
  "github.com/fatih/color"
)

type QueryType interface {
  bool | pir.Query[matrix.Elem64] | pir.Query[matrix.Elem32]
}

type AnsType interface {
  TiptoeHint | pir.Answer[matrix.Elem64] | pir.Answer[matrix.Elem32]
}

type Client struct {
  params          corpus.Params

  embClient       *pir.Client[matrix.Elem64]
  embSecret       *pir.SecretLHE[matrix.Elem64]
  embMap          database.ClusterMap
  embIndices      map[uint64]bool

  urlClient       *pir.Client[matrix.Elem32]
  urlSecret       *pir.Secret[matrix.Elem32]
  urlMap          database.SubclusterMap
  urlIndices      map[uint64]bool

  rpcClient       *rpc.Client
  useCoordinator  bool

  stepCount       int
}

func NewClient(useCoordinator bool) *Client {
  c := new(Client)
  c.useCoordinator = useCoordinator
  return c
}

func (c *Client) NumDocs() uint64 {
  return c.params.NumDocs
}

func (c *Client) NumClusters() int {
  if len(c.embMap) > 0 {
    return len(c.embMap)
  }
  return len(c.urlMap)
}

func readHint(hintFile string) *TiptoeHint {
    f, err := os.Open(hintFile)
    if err != nil {
      return nil
    }

    defer f.Close()

    hint := new(TiptoeHint)
    decoder := gob.NewDecoder(f)
    if decoder.Decode(&hint) != nil {
      return nil
    } 

    return hint
}

func saveHint(hintFile string, hint *TiptoeHint) {
    f, err := os.Create(hintFile)
    if err != nil {
      return
    }

    defer f.Close()

    encoder := gob.NewEncoder(f)
    encoder.Encode(hint)
}

func (c *Client) printStep(text string) {
  col := color.New(color.FgGreen).Add(color.Bold)
  col.Printf("%d) %v\n", c.stepCount, text)
  c.stepCount += 1
}

func RunClient(coordinatorAddr string, conf *config.Config, hintFile string) {
  color.Yellow("Setting up client...")

  c := NewClient(true /* use coordinator */)
  c.printStep("Getting hint")

  var hint *TiptoeHint
  if len(hintFile) > 0 {
    fmt.Println("\tAttempting to read hint from file", hintFile)
    hint = readHint(hintFile)
  }

  if hint == nil {
    fmt.Println("\tFetching hint from network", hintFile)
    hint = c.getHint(true /* keep conn */, coordinatorAddr)
    fmt.Println("\tWriting hint to file", hintFile)
    go saveHint(hintFile, hint) 
  }

  c.Setup(hint)
  logHintSize(hint)

  in, out := embeddings.SetupEmbeddingProcess(c.NumClusters(), conf)

  perfMax := 5
  perfC := make(chan Perf, perfMax)

  col := color.New(color.FgYellow).Add(color.Bold)

  go func() {
    for {
      perfC <- c.preprocessRound(false)
    }
  }()

  for {
    c.stepCount = 1
    c.printStep("Running client preprocessing for decryption")
    perf := <-perfC

    fmt.Printf("\tPreprocess buffer: %d/%d\n", len(perfC), perfMax)
    fmt.Printf("\n\n")
    col.Printf("Enter private search query: ")
    text := utils.ReadLineFromStdin()
    fmt.Printf("\n\n")
    if (strings.TrimSpace(text) == "") || (strings.TrimSpace(text) == "quit") {
      break
    }
    c.runRound(perf, in, out, text, coordinatorAddr, true /* verbose */, true /* keep conn */)
  }

  if c.rpcClient != nil {
    c.rpcClient.Close()
  }
  in.Close()
  out.Close()
}

func (c *Client) preprocessRound(verbose bool) Perf {
  var p Perf

  // Perform preprocessing
  start := time.Now()
  c.PreprocessQueryEmbeddings()
  c.PreprocessQueryUrls()
  p.clientPreproc = time.Since(start).Seconds()

  if verbose {
    fmt.Printf("  preprocessing complete -- %fs\n\n", p.clientPreproc)
  }

  return p
}

func (c *Client) runRound(p Perf, in io.WriteCloser, out io.ReadCloser, 
                          text, coordinatorAddr string, verbose, keepConn bool) Perf {
  y := color.New(color.FgYellow, color.Bold)
  fmt.Printf("Executing query \"%s\"\n", y.Sprintf(text))

  // Build embeddings query
  start := time.Now()
  if verbose {
    c.printStep("Generating embedding of the query")
  }

  var query struct {
    Cluster_index uint64
    Emb           []int8
  }

  io.WriteString(in, text + "\n") // send query to embedding process
  if err := json.NewDecoder(out).Decode(&query); err != nil { // get back embedding + cluster
    log.Printf("Did you remember to set up your python venv?")
    panic(err)
  }

  if query.Cluster_index >= uint64(c.NumClusters()) {
    panic("Should not happen")
  }

  if verbose {
    c.printStep(fmt.Sprintf("Building PIR query for cluster %d", query.Cluster_index))
  }

  embQuery := c.QueryEmbeddings(query.Emb, query.Cluster_index, true /* preprocessed */)
  p.clientSetup = time.Since(start).Seconds()

  // Send embeddings query to server
  if verbose {
    c.printStep("Sending SimplePIR query to server")
  }
  networkingStart := time.Now()
  embAns := c.getEmbeddingsAnswer(embQuery, true /* keep conn */, coordinatorAddr)
  p.t1, p.up1, p.down1 = logStats(c.params.NumDocs, networkingStart, embQuery, embAns)

  c.printStep("Decrypting server answer")
  // Recover document and URL chunk to query for
  embDec := c.ReconstructEmbeddingsWithinCluster(embAns, query.Cluster_index)
  scores := embeddings.SmoothResults(embDec, c.embClient.GetP())
  indicesByScore := utils.SortByScores(scores)
  docIndex := indicesByScore[0]

  if verbose {
    fmt.Printf("\tDoc %d within cluster %d has the largest inner product with our query\n",
               docIndex, query.Cluster_index)
    c.printStep(fmt.Sprintf("Building PIR query for url/title of doc %d in cluster %d", 
               docIndex, query.Cluster_index))
  }

  // Build URL query
  urlQuery, retrievedChunk := c.QueryUrls(query.Cluster_index, docIndex, true /* preprocessed */)

  // Send URL query to server
  if verbose {
    c.printStep(fmt.Sprintf("Sending PIR query to server for chunk %d", retrievedChunk))
  }
  networkingStart = time.Now()
  urlAns := c.getUrlsAnswer(urlQuery, keepConn, coordinatorAddr)
  p.t2, p.up2, p.down2 = logStats(c.params.NumDocs, networkingStart, urlQuery, urlAns)

  // Recover URLs of top 10 docs in chunk
  urls := c.ReconstructUrls(urlAns, query.Cluster_index, docIndex)
  if verbose {
    c.printStep("Reconstructed PIR answers.")
    fmt.Printf("\tThe top 10 retrieved urls are:\n")
  }

  j := 1
  for at := 0; at < len(indicesByScore); at++ {
    if scores[at] == 0 {
      break
    }

    doc := indicesByScore[at]
    _, chunk, index := c.urlMap.SubclusterToIndex(query.Cluster_index, doc)

    if chunk == retrievedChunk {
      if verbose {
        fmt.Printf("\t% 3d) [score %s] %s\n", j, 
          color.YellowString(fmt.Sprintf("% 4d", scores[at])),
          color.BlueString(corpus.GetIthUrl(urls, index)))
      }
      j += 1
      if j > 10 {
        break
      }
    }
  }

  p.clientTotal = time.Since(start).Seconds()
  fmt.Printf("\tAnswered in:\n\t\t%v (preproc)\n\t\t%v (client)\n\t\t%v (round 1)\n\t\t%v (round 2)\n\t\t%v (total)\n---\n", 
              p.clientPreproc, p.clientSetup, p.t1, p.t2, p.clientTotal)
 
  return p
}

func (c *Client) Setup(hint *TiptoeHint) {
  if hint == nil {
    panic("Hint is empty")
  }

  if hint.CParams.NumDocs == 0 {
    panic("Corpus is empty")
  }

  c.params = hint.CParams

  if hint.ServeEmbeddings {
    if hint.EmbeddingsHint.IsEmpty() {
      panic("Embeddings hint is empty")
    }

    c.embClient = utils.NewPirClient(&hint.EmbeddingsHint) 
    c.embMap = hint.EmbeddingsIndexMap
    c.embIndices = make(map[uint64]bool)
    for _, v := range c.embMap {
      c.embIndices[v] = true
    }

    fmt.Printf("\tEmbeddings client: %s\n", utils.PrintParams(c.embClient))
  }

  if hint.ServeUrls {
    if hint.UrlsHint.IsEmpty() {
      panic("Urls hint is empty")
    }
        
    c.urlClient = utils.NewPirClient(&hint.UrlsHint)
    c.urlMap = hint.UrlsIndexMap
    c.urlIndices = make(map[uint64]bool)
    for _, vals := range c.urlMap {
      for _, v := range vals {
        c.urlIndices[v.Index()] = true
      }
    }
  
    fmt.Printf("\tURL client: %s\n", utils.PrintParams(c.urlClient))
  }

  if hint.ServeUrls && hint.ServeEmbeddings && 
     (len(c.urlMap) != len(c.embMap)) {
    fmt.Printf("Both maps don't have the same length: %d %d\n", len(c.urlMap), len(c.embMap))
//    panic("Both maps don't have same length.")
  }
}

func (c *Client) PreprocessQueryEmbeddings() {
  if c.params.NumDocs == 0 {
    panic("Not set up")
  }
  c.embSecret = c.embClient.PreprocessQueryLHE()
}

func (c *Client) QueryEmbeddings(emb []int8, clusterIndex uint64, preprocessed bool) *pir.Query[matrix.Elem64] {
  if c.params.NumDocs == 0 {
    panic("Not set up")
  }

  if !preprocessed {
    c.embSecret = c.embClient.PreprocessQueryLHE()
  }

  dbIndex := c.embMap.ClusterToIndex(uint(clusterIndex))
  m := c.embClient.GetM()
  dim := uint64(len(emb))

  if m % dim != 0 {
    panic("Should not happen")
  }
  if dbIndex % dim != 0 {
    panic("Should not happen")
  }

  _, colIndex := database.Decompose(dbIndex, m)
  arr := matrix.Zeros[matrix.Elem64](m, 1)
  for j := uint64(0); j < dim; j++ {
    arr.AddAt(colIndex + j, 0, matrix.Elem64(emb[j]))
  }

  return c.embClient.QueryLHEPreprocessed(arr, c.embSecret)
}

func (c *Client) PreprocessQueryUrls() {
  if c.params.NumDocs == 0 {
    panic("Not set up")
  }
  c.urlSecret = c.urlClient.PreprocessQuery()
}

func (c *Client) QueryUrls(clusterIndex, docIndex uint64, 
                           preprocessed bool) (*pir.Query[matrix.Elem32], uint64) {
  if c.params.NumDocs == 0 {
    panic("Not set up")
  }

  if !preprocessed {
    c.urlSecret = c.urlClient.PreprocessQuery()
  }

  dbIndex, chunkIndex, _ := c.urlMap.SubclusterToIndex(clusterIndex, docIndex) 

  return c.urlClient.QueryPreprocessed(dbIndex, c.urlSecret), chunkIndex
}

func (c *Client) ReconstructEmbeddings(answer *pir.Answer[matrix.Elem64], 
                                       clusterIndex uint64) uint64 {
  vals := c.embClient.RecoverManyLHE(c.embSecret, answer)

  dbIndex := c.embMap.ClusterToIndex(uint(clusterIndex))
  rowIndex, _ := database.Decompose(dbIndex, c.embClient.GetM())
  res := vals.Get(rowIndex, 0)

  return uint64(res)
}

func (c *Client) ReconstructEmbeddingsWithinCluster(answer *pir.Answer[matrix.Elem64], 
                                                    clusterIndex uint64) []uint64 {
  dbIndex := c.embMap.ClusterToIndex(uint(clusterIndex))
  rowStart, colIndex := database.Decompose(dbIndex, c.embClient.GetM())
  rowEnd := database.FindEnd(c.embIndices, rowStart, colIndex,
                             c.embClient.GetM(), c.embClient.GetL(), 0)

  vals := c.embClient.RecoverManyLHE(c.embSecret, answer)

  res := make([]uint64, rowEnd - rowStart)
  at := 0
  for j := rowStart; j < rowEnd; j++ {
    res[at] = uint64(vals.Get(j, 0))
    at += 1
  }

  return res
}

func (c *Client) ReconstructUrls(answer *pir.Answer[matrix.Elem32], 
                                 clusterIndex, docIndex uint64) string {
  dbIndex, _, _ := c.urlMap.SubclusterToIndex(clusterIndex, docIndex)
  rowStart, colIndex := database.Decompose(dbIndex, c.urlClient.GetM())
  rowEnd := database.FindEnd(c.urlIndices, rowStart, colIndex, 
                             c.urlClient.GetM(), c.urlClient.GetL(), c.params.UrlBytes)

  vals := c.urlClient.RecoverMany(c.urlSecret, answer)

  out := make([]byte, rowEnd - rowStart)
  for i, e := range vals[rowStart:rowEnd] {
    out[i] = byte(e)
  }

  if c.params.CompressUrl {
    res, err := corpus.Decompress(out)
    for ; err != nil; {
      out = out[:len(out)-1]
      if len(out) == 0 {
        panic("Should not happen")
      }
      res, err = corpus.Decompress(out)
    }
    return strings.TrimRight(res, "\x00")
  }

  return strings.TrimRight(string(out), "\x00")
}

func makeRPC[Q QueryType, A AnsType](query *Q, reply *A, useCoordinator, keepConn bool, 
                                     tcp, rpc string, client *rpc.Client) *rpc.Client {
  if !useCoordinator {
    conn := utils.DialTCP(tcp)
    utils.CallTCP(conn, "Server." + rpc, query, reply)
    conn.Close()
  } else {
    if client == nil {
      client = utils.DialTLS(tcp)
    }

    utils.CallTLS(client, "Coordinator." + rpc, query, reply)

    if !keepConn {
      client.Close()
      client = nil
    }
  }

  return client
}

func (c *Client) getHint(keepConn bool, tcp string) *TiptoeHint {
  query := true
  hint := TiptoeHint{}
  c.rpcClient = makeRPC[bool, TiptoeHint](&query, &hint, c.useCoordinator, keepConn, 
                                          tcp, "GetHint", c.rpcClient)
  return &hint
}

func (c *Client) getEmbeddingsAnswer(query *pir.Query[matrix.Elem64], 
                                     keepConn bool, 
	  		             tcp string) *pir.Answer[matrix.Elem64] {
  ans := pir.Answer[matrix.Elem64]{}
  c.rpcClient = makeRPC[pir.Query[matrix.Elem64], pir.Answer[matrix.Elem64]](query, &ans, 
                                                                             c.useCoordinator, keepConn, 
									     tcp, "GetEmbeddingsAnswer",
								             c.rpcClient)
  return &ans
}

func (c *Client) getUrlsAnswer(query *pir.Query[matrix.Elem32], 
                               keepConn bool, 
			       tcp string) *pir.Answer[matrix.Elem32] {
  ans := pir.Answer[matrix.Elem32]{}
  c.rpcClient = makeRPC[pir.Query[matrix.Elem32], pir.Answer[matrix.Elem32]](query, &ans, 
                                                                             c.useCoordinator, keepConn, 
									     tcp, "GetUrlsAnswer",
								             c.rpcClient)
  return &ans
}

func (c *Client) closeConn() {
  if c.rpcClient != nil {
    c.rpcClient.Close()
    c.rpcClient = nil
  }
}
