package utils

import (
  "fmt"
  "sort"
  "bytes"
  "math/rand"
  "encoding/gob"
)

import (
  "github.com/henrycg/simplepir/pir"
  "github.com/henrycg/simplepir/matrix"
)

const letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "

type Number interface {
  int | int64 | uint | uint64
}

func RandString(n int) string {
  b := make([]byte, n)
  for i, _ := range b {
    b[i] = letters[rand.Intn(len(letters))]
  }
  return string(b)
}

func RandomIndex[N Number](max N) uint64 {
  return uint64(rand.Intn(int(max)))
}

func Max(arr []uint64) uint64 {
  res := uint64(0)
  for _, v := range arr {
    if v > res {
      res = v
    }
  }
  return res
}

func SortByScores(scores []int) []uint64 {
  score_to_index := make(map[int][]uint64)

  for i, v := range scores {
    if _, ok := score_to_index[v]; !ok {
      score_to_index[v] = make([]uint64, 0)
    }
    score_to_index[v] = append(score_to_index[v], uint64(i))
  }

  sort.Sort(sort.Reverse(sort.IntSlice(scores)))

  indices := make([]uint64, len(scores))
  at := 0
  for i, v := range scores {
    if at >= len(score_to_index[v]) {
      at = 0
    }
    indices[i] = score_to_index[v][at]
    at += 1
  }

  return indices
}

func BytesToMB(bytes uint64) float64 {
  return float64(bytes)/(1024*1024)
}

func BytesToKB(bytes uint64) float64 {
  return float64(bytes)/1024
}

func MessageSizeBytes(m interface{}) uint64 {
  var buf bytes.Buffer
  enc := gob.NewEncoder(&buf)

  var err error
  switch v := m.(type) {
    // necessary to register the right gob encoders
    case PIR_hint[matrix.Elem32]: 
      err = enc.Encode(&v)
    case PIR_hint[matrix.Elem64]:
      err = enc.Encode(&v)
    case pir.Query[matrix.Elem32]: 
      err = enc.Encode(&v)
    case pir.Query[matrix.Elem64]:
      err = enc.Encode(&v)
    case pir.Answer[matrix.Elem32]:
      err = enc.Encode(&v)
    case pir.Answer[matrix.Elem64]:
      err = enc.Encode(&v)
    case map[uint]uint64:
      err = enc.Encode(&v)
    case map[uint][]uint64:
      err = enc.Encode(&v)
    default:
      err = enc.Encode(&v)
      //panic("Bad input to message_size_bytes")
  }

  if err != nil {
    fmt.Println(err)
    panic("Should not happen")
  }

  return uint64(buf.Len())
}

func MessageSizeMB(m interface{}) float64 {
  return BytesToMB(MessageSizeBytes(m))
}

func MessageSizeKB(m interface{}) float64 {
  return BytesToKB(MessageSizeBytes(m))
}
