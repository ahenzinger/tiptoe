package corpus

import (
  "fmt"
  "testing"
)

func TestCompression(t *testing.T) {
  str := "We are working on private web search."
  b := Compress(str)
  cpy, err := Decompress(b)

  if err != nil || str != cpy {
    fmt.Printf("%s vs. %s\n", str, cpy)
    t.Fail()
  }
}
