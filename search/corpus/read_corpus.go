package corpus

import (
  "io"
  "fmt"
  "strconv"
  "strings"
  "bufio"
  "encoding/csv"
)

import (
  "github.com/ahenzinger/tiptoe/search/utils"
  "github.com/ahenzinger/tiptoe/search/config"
  "github.com/ahenzinger/tiptoe/search/embeddings"
)

func (p *Params) checkParams() {
  if p.SlotBits > 8 {
    panic("Not supported. Embeddings are represented as 8-bit values.")
  }
}

func ReadEmbeddingsCsv(file string) *Corpus {
  f := utils.OpenFile(file)
  defer f.Close()

  c := new(Corpus)
  var reader *csv.Reader
  reader, c.params.NumDocs, c.params.EmbeddingSlots, c.params.SlotBits = parseCsvHeader(f)
  c.params.checkParams()
  c.embeddings = make([]int8, c.params.EmbeddingSlots * c.params.NumDocs)
  c.embeddingsClusterMap = make(map[uint]uint)
  c.maxClusterId = uint(c.params.NumDocs - 1)

  slots := uint(c.params.EmbeddingSlots)

  for at := uint(0); ; at++ {
    row, err := reader.Read()
    if err == io.EOF {
      break
    } else if err != nil {
      fmt.Printf("%s\n", err)
      panic("Error reading CSV file")
    }

    offset := at * slots
    c.embeddingsClusterMap[at] = offset

    for i := uint(0); i < slots; i++ {
      u, err := strconv.Atoi(row[i])
      c.embeddings[offset+i] = embeddings.Clamp(u, c.params.SlotBits)
      if err != nil {
        panic("Error parsing CSV embeddings")
      }
    }
  }

  if uint64(len(c.embeddingsClusterMap)) != c.params.NumDocs {
    panic("Should not happen!")
  }

  return c
}

func ReadUrlsCsv(file string, compress bool) *Corpus {
  f := utils.OpenFile(file)
  defer f.Close()

  c := new(Corpus)
  var reader *csv.Reader
  reader, c.params.NumDocs, c.params.EmbeddingSlots, c.params.SlotBits = parseCsvHeader(f)
  c.params.CompressUrl = compress
  c.params.checkParams()
  c.urls = make([][]byte, c.params.NumDocs)
  c.urlClusterMap = make(map[uint][]Subcluster)
  c.maxClusterId = uint(c.params.NumDocs - 1)

  for at := uint(0); ; at++ {
    row, err := reader.Read()
    if err == io.EOF {
      break
    } else if err != nil {
      fmt.Printf("%s\n", err)
      panic("Error reading CSV file")
    }

    if compress {
      c.urls[at] = Compress(row[c.params.EmbeddingSlots + 1])
    } else {
      c.urls[at] = []byte(row[c.params.EmbeddingSlots + 1])
    }

    url_length := uint64(len(c.urls[at]))
    if url_length > c.params.UrlBytes {
      c.params.UrlBytes = url_length
    }

    // URL clustering not implemented in test corpuses; just make URL clusters of size 1.
    subcluster := Subcluster{
	    index: uint64(at), 
	    size: 1,
    }
    c.urlClusterMap[at] = []Subcluster{ subcluster }
  }

  if uint64(len(c.urlClusterMap)) != c.params.NumDocs {
    panic("Should not happen!")
  }

  return c
}

func ReadEmbeddingsTxt(clusterStart, clusterStop int, conf *config.Config) *Corpus {
  c := new(Corpus)
  c.params = Params{
    NumDocs: 0,
    EmbeddingSlots : conf.EMBEDDINGS_DIM(),
    SlotBits: config.SLOT_BITS(),
  }
  c.params.checkParams()

  c.embeddings = make([]int8, 0)
  c.embeddingsClusterMap = make(map[uint]uint)

  if clusterStop > conf.TOTAL_NUM_CLUSTERS() {
    clusterStop = conf.TOTAL_NUM_CLUSTERS()
  }

  c.maxClusterId = uint(clusterStop - 1)

  for cluster := clusterStart; cluster < clusterStop; cluster++ {
    c.embeddingsClusterMap[uint(cluster)] = uint(len(c.embeddings))

    file := conf.TxtCorpus(cluster)
    f := utils.OpenFile(file) // Previously didn't fail if file doesn't exist here (os.IsNotExist(err))
    defer f.Close()

    scanner := bufio.NewScanner(f)

    for scanner.Scan() {
      txt := scanner.Text()
  
      if len(txt) == 0 {
	continue
      } else if txt == SUBCLUSTER_DELIM { // ignore URL subclusters in embeddings step
        continue
      }

      vals := parseEmbeddingsTxt(txt)
      if len(vals) != int(c.params.EmbeddingSlots) {
	fmt.Println(txt)
	fmt.Printf("%d vs. %d\n", len(vals), c.params.EmbeddingSlots)
	fmt.Printf("Failed on file %s\n", file)
        panic("Corpus embedding dimension does not match expected.")
      }
      
      emb := make([]int8, c.params.EmbeddingSlots)
      for i := uint64(0); i < c.params.EmbeddingSlots; i++ {
        u, err := strconv.Atoi(vals[i])
	if err != nil {
	  fmt.Println(vals[i])
	  fmt.Println(u)
	  fmt.Println(err)
	  panic("Error parsing corpus emebddings")
	}
	emb[i] = embeddings.Clamp(int(u), c.params.SlotBits)
      }

      c.embeddings = append(c.embeddings, emb...)
      c.params.NumDocs += 1
    }

    if err := scanner.Err(); err != nil {
      fmt.Println(err)
      fmt.Println(file)
      panic("Error reading file")
    }
  }

  fmt.Printf("Read %d docs\n", c.params.NumDocs)
  if uint64(len(c.embeddings)) != c.params.NumDocs * c.params.EmbeddingSlots {
    panic("Should not happen!")
  }

  return c
}

func ReadUrlsTxt(clusterStart, clusterStop int, conf *config.Config) *Corpus {
  c := new(Corpus)
  c.params = Params{
    NumDocs: 0,
    CompressUrl: true,
  }
  c.params.checkParams()

  c.urls = make([][]byte, 0)
  c.urlClusterMap = make(map[uint][]Subcluster)

  if clusterStop > conf.TOTAL_NUM_CLUSTERS() {
    clusterStop = conf.TOTAL_NUM_CLUSTERS()
  }

  c.maxClusterId = uint(clusterStop - 1)

  for cur := clusterStart; cur < clusterStop; cur++ {
    file := conf.TxtCorpus(cur)
    f := utils.OpenFile(file) // Previously didn't fail if file doesn't exist here (os.IsNotExist(err))
    defer f.Close()

    scanner := bufio.NewScanner(f)
    urls := make([][]string, 1)
    urls[0] = make([]string, 0)
    subclusterNum := 0

    for scanner.Scan() {
      txt := scanner.Text()
      if len(txt) == 0 {
	continue
      } else if txt == SUBCLUSTER_DELIM {
	subclusterNum += 1
	urls = append(urls, []string{})
      } else {
	url := parseUrlTxt(txt)
        if len(url) > MAX_URL_LEN {
          url = "0000"
        }
	urls[subclusterNum] = append(urls[subclusterNum], url) 
      }
    }

    if err := scanner.Err(); err != nil {
      fmt.Println(err)
      fmt.Println(file)
      panic("Error reading file")
    }

    if len(urls[subclusterNum]) == 0 {
      urls = urls[:subclusterNum]
    }

    ch := make(chan bool)
    compressed := make([][]byte, len(urls))
    lengths := make([]uint64, len(urls))
    for sc := 0; sc < len(urls); sc++ {
      go func(i int) {
	lengths[i] = uint64(len(urls[i]))
	txt := strings.Join(urls[i], URL_DELIM)
	compressed[i] = Compress(txt)
	ch <- true
      }(sc)
    }

    utils.ReadFromChannel(ch, len(urls), false)

    if _, ok := c.urlClusterMap[uint(cur)]; ok {
      panic("Key should not exist.")
    }
    c.urlClusterMap[uint(cur)] = make([]Subcluster, len(urls))

    for sc := 0; sc < len(urls); sc++ {
      compressed := compressed[sc]
      num := lengths[sc]

      l := uint64(len(c.urls))
      c.urls = append(c.urls, compressed)
      c.params.NumDocs += num

      chunk := Subcluster{
	      index: l, 
	      size: num,
      }
      c.urlClusterMap[uint(cur)][sc] = chunk

      length := uint64(len(compressed))
      if length > c.params.UrlBytes {
        c.params.UrlBytes = length
      }
    }

    if cur % 100 == 0 {
      fmt.Printf("Finished cluster %d\n", cur)
    }
  }

  fmt.Printf("Read %d docs\n", c.params.NumDocs)
  return c
}
