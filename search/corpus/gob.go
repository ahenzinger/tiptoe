package corpus

import (
  "bytes"
  "encoding/gob"
)

func (c *Subcluster) GobEncode() ([]byte, error) {
  buf := new(bytes.Buffer)
  enc := gob.NewEncoder(buf)
  if err := enc.Encode(c.index); err != nil {
    return buf.Bytes(), err
  }

  err := enc.Encode(c.size)
  return buf.Bytes(), err
}

func (c *Subcluster) GobDecode(buf []byte) error {
  b := bytes.NewBuffer(buf)
  dec := gob.NewDecoder(b)
  if err := dec.Decode(&c.index); err != nil {
    return err
  }

  err := dec.Decode(&c.size)
  return err
}
