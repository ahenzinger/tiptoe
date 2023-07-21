package embeddings

import (
  "io"
  "time"
  "strconv"
  "os/exec"
  "math/rand"
)

import (
  "github.com/ahenzinger/tiptoe/search/config"
)

func SetupEmbeddingProcess(numClusters int, conf *config.Config) (io.WriteCloser, io.ReadCloser) {
  preamble := conf.PREAMBLE()
  if preamble == "/data/pdos/web-search/" {
    preamble += "cluster_centroids/"
  }

  toRun := "embeddings/embed_text.py"
  if conf.IMAGE_SEARCH() {
    toRun = "embeddings/embed_img.py"
  }

  cmd := exec.Command("python3", toRun, preamble, strconv.Itoa(numClusters))
  stdin, err1 := cmd.StdinPipe()
  if err1 != nil {
    panic(err1)
  }

  stdout, err2 := cmd.StdoutPipe()
  if err2 != nil {
    panic(err2)
  }

  if err := cmd.Start(); err != nil {
    panic(err)
  }

  time.Sleep(5 * time.Second) // So the python process has time to start up

  return stdin, stdout
}

func RandomEmbedding(length, mod uint64) []int8 {
  vals := make([]int8, length)

  for i := uint64(0); i < length; i++ {
    vals[i] = int8(rand.Intn(int(mod)))
    if rand.Intn(2) == 1 {
      vals[i] *= -1
    }
  }

  return vals
}

func ShrinkPrecision(emb []int, slot_bits uint64) []int8 {
  arr := make([]int8, len(emb))
  for i, v := range emb {
    arr[i] = Clamp(v, slot_bits)
  }
  return arr
}

func InnerProduct(v1, v2 []int8) int {
  if len(v1) != len(v2) {
    panic("Length mismatch")
  }

  res := int(0)
  for i, _ := range v1 {
    a := int(v1[i])
    b := int(v2[i])
    res += a * b
  }

  return res
}

func SmoothResult(val uint64, mod uint64) int {
  if val > mod {
    panic("Should not happen")
  }

  if val > mod / 2 {
    return int(val - mod)
  }

  return int(val)
}

func SmoothResults(vals []uint64, mod uint64) []int {
  res := make([]int, len(vals))

  for i := 0; i < len(vals); i++ {
    res[i] = SmoothResult(vals[i], mod)
  }

  return res
}

func Clamp(val int, slotBits uint64) int8 {
  min := -int(1 << (slotBits-1))
  if val <= min {
    return int8(min)
  }

  max := int(1 << (slotBits-1))
  if val > max {
    return int8(max)
  }

  return int8(val)
}
