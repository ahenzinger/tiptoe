package corpus

import (
  "fmt"
  "strings"
)

type Params struct {
  NumDocs         uint64       // number of docs in corpus
  EmbeddingSlots  uint64       // number of slots per embedding
  SlotBits        uint64       // precision of each slot (in bits)
  UrlBytes        uint64       // max bytes/url -- after optional compression
  CompressUrl     bool         // whether the urls are compressed with gzip
}

type Corpus struct {
  params                Params

  embeddings            []int8
  embeddingsClusterMap  map[uint]uint

  urls                  [][]byte
  urlClusterMap         map[uint][]Subcluster

  maxClusterId          uint
}

func (c *Corpus) GetParams() Params {
  return c.params
}

func (c *Corpus) GetEmbeddingSlots() uint64 {
  return c.params.EmbeddingSlots
}

func (c *Corpus) GetNumDocs() uint64 {
  return c.params.NumDocs
}

func (c *Corpus) GetSlotBits() uint64 {
  return c.params.SlotBits
}

func (c *Corpus) GetUrlBytes() uint64 {
  return c.params.UrlBytes
}

func (c *Corpus) GetCompressUrl() bool {
  return c.params.CompressUrl
}

func (c *Corpus) NumClusters() int {
  return len(c.embeddingsClusterMap)
}

func (c *Corpus) NumSubclusters() int {
  return len(c.urls)
}

func (c *Corpus) NumSubclustersInCluster(i uint) int {
  if _, ok := c.urlClusterMap[i]; !ok {
    panic("Cluster does not exist")
  }
  return len(c.urlClusterMap[i])
}

func (c *Corpus) Clusters() []uint {
  keys := make([]uint, 0, len(c.embeddingsClusterMap))
  for k, _ := range c.embeddingsClusterMap {
    keys = append(keys, k)
  }
  return keys
}

func (c *Corpus) ClusterToIndex(i uint) uint {
  if _, ok := c.embeddingsClusterMap[i]; !ok {
    panic("Cluster does not exist")
  }
  return c.embeddingsClusterMap[i]
}

func (c *Corpus) NumDocsInCluster(i uint) uint64 {
  startIndex := c.ClusterToIndex(i)

  var endIndex uint
  if i == c.maxClusterId { // WARNING: Implementation changed here.
    endIndex = uint(len(c.embeddings))
  } else {
    // NOTE: Cluster names must be consecutive. So next cluster should exist...
    endIndex = c.ClusterToIndex(i + 1)
  }

  numSlots := uint64(endIndex - startIndex)
  if numSlots % c.params.EmbeddingSlots != 0 {
    panic("Should not happen")
  }

  if DISALLOW_EMPTY_CLUSTERS && (endIndex == startIndex) {
    fmt.Printf("Getting size of cluster %d; starts and ends at %d, %d\n", i, endIndex, startIndex)
    panic("Cluster has size 0. Should not happen.")
  }

  return numSlots / c.params.EmbeddingSlots
}

func (c *Corpus) GetEmbedding(index uint64) []int8 {
  emb := make([]int8, c.params.EmbeddingSlots)
  copy(emb, c.embeddings[index:index + c.params.EmbeddingSlots])
  return emb
}

func (c *Corpus) IndexOfSubclusterWithinCluster(cluster, sc uint) int {
  if _, ok := c.urlClusterMap[cluster]; !ok {
    panic("Cluster does not exist")
  }

  for i, e := range c.urlClusterMap[cluster] {
    if e.Index() == uint64(sc) {
      return i
    }
  }

  panic("Subcluster does not exist within cluster")
}

// Returns size in bytes
func (c *Corpus) SizeOfSubcluster(i uint) int {
  return len(c.urls[i])
}

func (c *Corpus) SizeOfSubclusterByIndex(cluster uint, index int) int {
  if _, ok := c.urlClusterMap[cluster]; !ok {
    panic("Cluster does not exist")
  }

  if index >= len(c.urlClusterMap[cluster]) {
    panic("Subcluster does not exist within cluster")
  }

  return int(c.urlClusterMap[cluster][index].Size())
}

func (c *Corpus) GetSubcluster(index uint) []byte {
  sc := make([]byte, len(c.urls[index]))
  copy(sc, c.urls[index])
  return sc
}

func (c *Corpus) SubclusterToClusterMap() map[uint]uint {
  index := make(map[uint]uint)

  for cluster, contents := range c.urlClusterMap {
    for _, sc := range contents {
      index[uint(sc.Index())] = cluster
    }
  }

  return index
}

func (c *Corpus) GetUrlsInCluster(i uint64) string {
  num := c.NumSubclustersInCluster(uint(i))
  chunks := make([]string, num)

  for ch := 0; ch < num; ch++ {
    at := c.urlClusterMap[uint(i)][ch].Index()

    if c.params.CompressUrl {
      url_chunk, err := Decompress(c.urls[at])
      if err != nil {
        panic("URL recovery failed")
      }
      chunks[ch] = url_chunk
    } else {
      chunks[ch] = strings.TrimRight(string(c.urls[at]), "\x00")
    }
  }

  return strings.Join(chunks, "")
}

func (p *Params) Consistent(np *Params) bool {
  if (p.EmbeddingSlots != np.EmbeddingSlots) ||
     (p.SlotBits != np.SlotBits) ||
     (p.CompressUrl != np.CompressUrl) {
    fmt.Println(np)
    fmt.Println(p)
    return false
  }
  return true
}
