package packing

import (
  "fmt"
  "sort"
)

import (
  "github.com/ahenzinger/tiptoe/search/corpus"
)

type Chunk struct {
  size    uint64
  index   uint64
}

type chunkSorter struct{
  chunks []Chunk
}

func ReverseSort(chunks []Chunk) {
  s := &chunkSorter{
    chunks: chunks,
  }

  sort.Sort(s)

  N := len(s.chunks)
  if N > 1 && s.chunks[0].size < s.chunks[N-1].size {
    panic("Sort did not work")
  }
}

func (s *chunkSorter) Len() int {
  return len(s.chunks)
}

func (s *chunkSorter) Swap(i, j int) {
  s.chunks[i], s.chunks[j] = s.chunks[j], s.chunks[i]
}

// WARNING: Flipped, because want to sort in reverse order!
func (s *chunkSorter) Less(i, j int) bool {
  return s.chunks[i].size > s.chunks[j].size
}

func BuildUrlChunks(corpus *corpus.Corpus) ([]Chunk, uint64) {
  chunks := make([]Chunk, corpus.NumSubclusters())

  actual_sz := uint64(0)
  for i := uint64(0); i < uint64(corpus.NumSubclusters()); i++ {
    chunks[i].index = i
    chunks[i].size = uint64(corpus.SizeOfSubcluster(uint(i)))
    actual_sz += chunks[i].size
  }

  return chunks, actual_sz
}

func BuildEmbChunks(corpus *corpus.Corpus) ([]Chunk, uint64) {
  chunks := make([]Chunk, corpus.NumClusters())

  clusters := corpus.Clusters()
  for i, cluster := range clusters {
    chunks[i].index = uint64(cluster)
    chunks[i].size = corpus.NumDocsInCluster(cluster)
  }

  return chunks, corpus.GetNumDocs() * corpus.GetEmbeddingSlots()
}

// Implements offline first-fit decreasing (at most 4/3x bigger than the optimal packing).
// Note: If the longest chunk is bigger than the max capacity, the max capacity will be exceeded.
func PackChunks(chunks []Chunk, maxCapacity uint64) ([][]uint, []uint64) {
  N := uint64(len(chunks))
  if N == 0 {
    panic("No chunks given")
  }

  ReverseSort(chunks) 
  fmt.Printf("The longest row has length %d -- max capacity is %d\n", chunks[0].size, maxCapacity)
  if chunks[0].size > maxCapacity {
    //panic("Rows are too long to pack!")
    maxCapacity = chunks[0].size
  }

  cols := make([][]uint, 1)
  cols[0] = []uint{ uint(chunks[0].index) } 

  col_szs := []uint64{ chunks[0].size }

  for i := uint64(1); i < N; i++ {
    fit := false
    for j := 0; j < len(cols); j++ {
      if col_szs[j] + chunks[i].size < maxCapacity {
        col_szs[j] += chunks[i].size
        cols[j] = append(cols[j], uint(chunks[i].index))
        fit = true
        break
      }
    }

    if !fit {
      new_col := []uint{ uint(chunks[i].index) }
      cols = append(cols, new_col)
      col_szs = append(col_szs, chunks[i].size)
    }
  }

  return cols, col_szs
}
