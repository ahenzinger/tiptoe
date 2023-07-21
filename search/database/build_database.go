package database

import (
  "fmt"
)

import (
  "github.com/henrycg/simplepir/pir"
  "github.com/henrycg/simplepir/lwe"
  "github.com/henrycg/simplepir/rand"
  "github.com/henrycg/simplepir/matrix"
)

import (
  "github.com/ahenzinger/tiptoe/search/utils"
  "github.com/ahenzinger/tiptoe/search/corpus"
  "github.com/ahenzinger/tiptoe/search/config"
  "github.com/ahenzinger/tiptoe/search/packing"
)

func BuildUrlsDatabase(c *corpus.Corpus, seed *rand.PRGKey, 
                       hintSz uint64) (*pir.Database[matrix.Elem32], SubclusterMap) {

  d := uint64(8) // num bits in a byte
  l := uint64(c.GetUrlBytes())
  logQ := uint64(32)

  if hintSz * 250 > l {
    fmt.Printf("Increasing L from %d to %d\n", l, hintSz*250)
    l = hintSz * 250
  } else {
    fmt.Printf("Hint size is %d MB\n", l/250)
    //panic("Cannot achieve hint size.")
  }

  // Bin packing of strings into database columns
  chunks, actualSz := packing.BuildUrlChunks(c)
  cols, colSzs := packing.PackChunks(chunks, l)

  m := uint64(len(cols))
  l = utils.Max(colSzs)
  fmt.Printf("DB size is %d -- best possible would be %d\n", l * m, actualSz)

  // Pick SimplePIR params
  p := lwe.NewParamsFixedP(logQ, m, 256 /* 2^8 */)
  if p == nil || p.Logq != 32 {
    panic("Failure in picking SimplePIR DB parameters")
  }

  subclusterToCluster := c.SubclusterToClusterMap()

  // Store strings in database
  vals := make([]uint64, l * m)
  indexMap := make(map[uint][]corpus.Subcluster)
  for colIndex, colContents := range cols {
    rowIndex := uint64(0)
    for _, subcluster := range colContents {
      cluster := subclusterToCluster[subcluster]
      if _, ok := indexMap[cluster]; !ok {
        indexMap[cluster] = make([]corpus.Subcluster, c.NumSubclustersInCluster(cluster))
      }

      arr := c.GetSubcluster(subcluster) // WARNING: copies the array under the hood
      i := c.IndexOfSubclusterWithinCluster(cluster, subcluster)
      sz := uint64(c.SizeOfSubclusterByIndex(cluster, i))
      indexMap[cluster][i].SetIndex(DBIndex(rowIndex, uint64(colIndex), m))
      indexMap[cluster][i].SetSize(sz)  

      for j := 0; j < len(arr); j++ {
        vals[DBIndex(rowIndex, uint64(colIndex), m)] = uint64(arr[j])
	rowIndex += 1
	if rowIndex > l {
          panic("Should not happen")
	}
      }
    }
  }

  db := pir.NewDatabaseFixedParams[matrix.Elem32](l * m, d, vals, p)

  if db.Info.L != l {
    panic("Should not happen")
  }

  return db, indexMap
}

func BuildEmbeddingsDatabase(c *corpus.Corpus, seed *rand.PRGKey, 
                             hintSz uint64, conf *config.Config) (*pir.Database[matrix.Elem64], ClusterMap) {
  l := hintSz * 125
  logQ := uint64(64)

  fmt.Printf( "  Building db with %d embeddings\n", c.GetNumDocs())

  // Bin packing of clusters into database columns
  chunks, actualSz := packing.BuildEmbChunks(c)
  cols, colSzs := packing.PackChunks(chunks, l)

  m := uint64(len(cols)) * c.GetEmbeddingSlots()
  l = utils.Max(colSzs)
  fmt.Printf("DB size is %d -- best possible would be %d\n", l*m, actualSz)
  
  // Pick SimplePIR params
  recordLen := conf.SIMPLEPIR_EMBEDDINGS_RECORD_LENGTH()
  p := lwe.NewParamsFixedP(logQ, m, (1 << recordLen))
  if (p == nil) || (p.P < uint64(1 << c.GetSlotBits())) || (p.Logq != 64) {
    fmt.Printf("P = %d; LogQ = %d\n", p.P, p.Logq)
    panic("Failure in picking SimplePIR DB parameters")
  }

  // Store embddings in database, such that clusters are kept together in a column
  vals := make([]uint64, l * m)
  indexMap := make(map[uint]uint64)
  slots := c.GetEmbeddingSlots()

  for colIndex, colContents := range cols {
    rowIndex := uint64(0)
    for _, clusterIndex := range colContents {
      if _, ok := indexMap[clusterIndex]; ok {
        panic("Key should not yet exist")
      }

      indexMap[clusterIndex] = DBIndex(rowIndex, slots * uint64(colIndex), m)
     
      sz := c.NumDocsInCluster(clusterIndex)
      start := uint64(c.ClusterToIndex(clusterIndex))

      for x := uint64(0); x < sz; x++ {
        arr := c.GetEmbedding(start) // WARNING: This copies the array
        for j := uint64(0); j < slots; j++ {
          vals[DBIndex(rowIndex, slots * uint64(colIndex) + j, m)] = uint64(arr[j])
        }
	start += slots
	rowIndex += 1
	if rowIndex > l {
	  panic("Should not happen")
	}
      }
    }
  }

  db := pir.NewDatabaseFixedParams[matrix.Elem64](l * m, uint64(recordLen), vals, p)
  fmt.Printf("DB dimensions: %d by %d\n", db.Info.L, db.Info.M)

  if db.Info.L != l {
    panic("Should not happen")
  }

  return db, indexMap
}
