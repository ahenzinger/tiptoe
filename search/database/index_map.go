package database

import (
  "fmt"
)

import (
  "github.com/ahenzinger/tiptoe/search/corpus"
)

type ClusterMap     map[uint]uint64
type SubclusterMap  map[uint][]corpus.Subcluster

func Decompose(index, M uint64) (uint64, uint64) {
  row := index / M
  col := index % M
  return row, col
}

func DBIndex(row, col, M uint64) uint64 {
  return row * M + col
}

func (m ClusterMap) ClusterToIndex(cluster uint) uint64 {
  i, ok := m[cluster]
  if !ok {
    fmt.Printf("Looked up cluster %d\n", cluster)
    panic("Cluster does not exist")
  }
  return i
}

func (m SubclusterMap) SubclusterToIndex(clusterIndex, docIndex uint64) (uint64, uint64, uint64) {
  cl, ok := m[uint(clusterIndex)]
  if !ok {
    fmt.Printf("Looked up cluster %d\n", clusterIndex)
    panic("Cluster does not exist")
  }

  if len(cl) == 0 {
    fmt.Printf("Looked up cluster %d\n", clusterIndex)
    panic("Cluster is empty")
  }

  chunk := uint64(0)
  prev := uint64(0)
  for at := cl[0].Size(); at <= docIndex; at += cl[chunk].Size() {
    chunk += 1

    if chunk >= uint64(len(cl)) {
      fmt.Printf("Looking for doc %d in cluster %d\n", docIndex, clusterIndex)
      panic("Chunk is not long enough.")
    }

    prev += cl[chunk - 1].Size()
  }

  // returns (index of subcluster in DB, retrieved subcluster, index within subcluster)
  return cl[chunk].Index(), chunk, docIndex - prev
}

func FindEnd(indices map[uint64]bool, rowStart, colIndex, M, L, maxLen uint64) uint64 {
  rowEnd := rowStart + 1
  for length := uint64(1); ; length++ {
    if (maxLen > 0) && (length >= maxLen) {
      break
    }
    if _, ok := indices[DBIndex(rowEnd, colIndex, M)]; ok {
      break
    }
    if rowEnd >= L {
      break
    }
    rowEnd += 1
  }

  return rowEnd
}

func (m SubclusterMap) FakeIndexInSubcluster(clusterIndex, subclusterIndex uint64) uint64 {
  cl, ok := m[uint(clusterIndex)]
  if !ok {
    fmt.Printf("Looked up cluster %d\n", clusterIndex)
    panic("Cluster does not exist")
  }

  at := uint64(0)
  for ch := uint64(0); ch < subclusterIndex; ch++ {
    at += cl[ch].Size()
  }

  return at
}

func mergeIndex(index, M, addtl_M uint64, shift_col bool) uint64 {
  row, col := Decompose(index, M)

  if shift_col {
    col += addtl_M
  }

  new_index := row * (M + addtl_M) + col
  return new_index
}

func MergeClusterMap(origMap ClusterMap, newMap ClusterMap, origM uint64, newM uint64) {
  for k, v := range origMap {
    origMap[k] = mergeIndex(v, origM, newM, false)
  }

  for k, v := range newMap {
    if _, ok := origMap[k]; ok {
      panic("Key should not be present")
    }
    origMap[k] = mergeIndex(v, newM, origM, true)
  }
}

func MergeSubclusterMap(origMap SubclusterMap, newMap SubclusterMap, origM uint64, newM uint64) {
  for k, v := range origMap {
    for i, val := range v {
      index := val.Index()
      origMap[k][i].SetIndex(mergeIndex(index, origM, newM, false))
    }
  }

  for k, v := range newMap {
    if _, ok := origMap[k]; ok {
      panic("Key should not be present")
    }

    origMap[k] = make([]corpus.Subcluster, len(v))
    copy(origMap[k], v)
    for i, val := range v {
      index := val.Index()
      origMap[k][i].SetIndex(mergeIndex(index, newM, origM, true))
    }
  }
}
