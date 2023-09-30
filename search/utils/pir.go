package utils

import (
  "fmt"
)

import (
  "github.com/henrycg/simplepir/pir"
  "github.com/henrycg/simplepir/rand"
  "github.com/henrycg/simplepir/matrix"
  "github.com/ahenzinger/underhood/underhood"
)

type PIR_hint[T matrix.Elem] struct {
  Info    pir.DBInfo
  Hint    matrix.Matrix[T]

  Seeds    []rand.PRGKey
  Offsets  []uint64
}

func (h *PIR_hint[T]) IsEmpty() bool {
  return (h.Hint.Cols() == 0)
}

func MergeHints[T matrix.Elem](h *PIR_hint[T], nh PIR_hint[T]) {
  // Check that DB info matches
  if (h.Info.Params.N != nh.Info.Params.N) ||
     (h.Info.Params.Sigma != nh.Info.Params.Sigma) ||
     (h.Info.Params.Logq != nh.Info.Params.Logq) ||
     (h.Info.Params.P != nh.Info.Params.P) {
    fmt.Printf("%#v vs. %#v\n", h.Info.Params, nh.Info.Params)
    panic("Parameter mismatch")
  }

  if (h.Info.RowLength != nh.Info.RowLength) ||
     (h.Info.Ne != nh.Info.Ne) ||
     (h.Info.X != nh.Info.X) ||
     (h.Info.Squishing != nh.Info.Squishing) {
    fmt.Println(h.Info)
    fmt.Println(nh.Info)
    panic("DB info mismatch")
  }

  // Update DB info
  h.Info.Params.M += nh.Info.Params.M
  h.Info.M += nh.Info.M
  if nh.Info.L > h.Info.L {
    h.Info.L = nh.Info.L
  }
  h.Info.Num += nh.Info.Num

  // Update DB hint
  h.Hint.AddWithMismatch(&nh.Hint)
  if h.Hint.Rows() != h.Info.L {
    panic("Should not happen")
  }

  // Update seeds
  h.Seeds = append(h.Seeds, nh.Seeds...)

  // Update offsets
  h.Offsets = append(h.Offsets, nh.Offsets...)
  if len(h.Seeds) != len(h.Offsets) {
    panic("Should not happen")
  }
}

func NewPirClient[T matrix.Elem](h *PIR_hint[T]) *pir.Client[T] {
  return pir.NewClientDistributed(&h.Hint, h.Seeds, h.Offsets, &h.Info)
}

func NewUnderhoodClient[T matrix.Elem](h *PIR_hint[T]) *underhood.Client[T] {
  return underhood.NewClientDistributed[T](h.Seeds, h.Offsets, &h.Info)
}

func PrintParams(i *pir.DBInfo) string {
  return fmt.Sprintf("M = %d; L = %d; p = %d; n = %d", i.M, i.L, i.Params.P, i.Params.N)
}
