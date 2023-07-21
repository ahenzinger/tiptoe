package utils

// NOTE: Only tests SimplePIR.

import (
  "fmt"
  "testing"
)

import (
  "github.com/henrycg/simplepir/pir"
  "github.com/henrycg/simplepir/lwe"
  "github.com/henrycg/simplepir/matrix"
  "github.com/henrycg/simplepir/rand"
)

func TestSimplePir32(t *testing.T) {
  N := uint64(1 << 20)
  d := uint64(8)
  i := uint64(23435)

  seedA := rand.RandomPRGKey() 
  p := lwe.NewParamsFixedP(32, (1 << 10), 512)
  db := pir.NewDatabaseRandomFixedParams[matrix.Elem32](rand.NewRandomBufPRG(), N, d, p)

  server := pir.NewServerSeed[matrix.Elem32](db, seedA)
  client := pir.NewClient[matrix.Elem32](server.Hint(), seedA, server.DBInfo())

  secret, query := client.Query(i)
  answer := server.Answer(query)
  val := client.Recover(secret, answer)

  if db.GetElem(i) != val {
    fmt.Printf("Got %d instead of %d\n", val, db.GetElem(i))
    panic("Reconstruct failed")
  }
}

func TestSimplePir64(t *testing.T) {
  N := uint64(1 << 20)
  d := uint64(17)
  i := uint64(23435)

  seedA := rand.RandomPRGKey() 
  p := lwe.NewParamsFixedP(64, (1 << 10), (1 << 17))
  db := pir.NewDatabaseRandomFixedParams[matrix.Elem64](rand.NewRandomBufPRG(), N, d, p)

  server := pir.NewServerSeed[matrix.Elem64](db, seedA)
  client := pir.NewClient[matrix.Elem64](server.Hint(), seedA, server.DBInfo())

  secret, query := client.Query(i)
  answer := server.Answer(query)
  val := client.Recover(secret, answer)

  if db.GetElem(i) != val {
    fmt.Printf("Got %d instead of %d\n", val, db.GetElem(i))
    panic("Reconstruct failed")
  }
}

func TestSimplePirLHE32(t *testing.T) {
  N := uint64(1 << 20)
  d := uint64(8)

  p := lwe.NewParamsFixedP(32, (1 << 10), 512)
  db := pir.NewDatabaseRandomFixedParams[matrix.Elem32](rand.NewRandomBufPRG(), N, d, p)

  server := pir.NewServer[matrix.Elem32](db)
  client := pir.NewClient[matrix.Elem32](server.Hint(), server.MatrixA(), server.DBInfo())

  arr := matrix.Rand[matrix.Elem32](rand.NewRandomBufPRG(), p.M, 1, p.P)

  secret, query := client.QueryLHE(arr)
  answer := server.Answer(query)
  vals := client.RecoverManyLHE(secret, answer)
  if vals.Cols() != 1 || vals.Rows() <= 1 {
    vals.Dim()
    panic("Should not happen")
  }

  shouldBe := matrix.Mul(db.Data, arr)
  shouldBe.ModConst(matrix.Elem32(db.Info.P()))

  if !shouldBe.Equals(vals) {
    panic("Reconstruct failed")
  }
}

func TestSimplePirLHE64(t *testing.T) {
  N := uint64(1 << 20)
  d := uint64(17)

  seedA := rand.RandomPRGKey()
  p := lwe.NewParamsFixedP(64, (1 << 10), (1 << 17))
  db := pir.NewDatabaseRandomFixedParams[matrix.Elem64](rand.NewRandomBufPRG(), N, d, p)

  server := pir.NewServerSeed[matrix.Elem64](db, seedA)
  client := pir.NewClient[matrix.Elem64](server.Hint(), seedA, server.DBInfo())

  arr := matrix.Rand[matrix.Elem64](rand.NewRandomBufPRG(), p.M, 1, p.P)

  secret, query := client.QueryLHE(arr)
  answer := server.Answer(query)
  vals := client.RecoverManyLHE(secret, answer)
  if vals.Cols() != 1 || vals.Rows() <= 1 {
    vals.Dim()
    panic("Should not happen")
  }

  shouldBe := matrix.Mul(db.Data, arr)
  shouldBe.ModConst(matrix.Elem64(db.Info.P()))
  
  if !shouldBe.Equals(vals) {
    panic("Reconstruct failed")
  }
}
