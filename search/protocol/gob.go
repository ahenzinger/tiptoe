package protocol

import (
  "os"
  "bytes"
  "encoding/gob"
)

type TiptoeServer interface {
  Server | Coordinator
}

func (k *Coordinator) GobEncode() ([]byte, error) {
  buf := new(bytes.Buffer)
  enc := gob.NewEncoder(buf)
  err := enc.Encode(k.numEmbServers)
  if err != nil {
    return buf.Bytes(), err
  }

  err = enc.Encode(k.embServerAddrs)
  if err != nil {
    return buf.Bytes(), err
  }

  err = enc.Encode(k.numUrlServers)
  if err != nil {
    return buf.Bytes(), err
  }

  err = enc.Encode(k.urlServerAddrs)
  if err != nil {
    return buf.Bytes(), err
  }

  err = enc.Encode(k.hint)
  return buf.Bytes(), err
}

func (s *Server) GobEncode() ([]byte, error) {
  buf := new(bytes.Buffer)
  enc := gob.NewEncoder(buf)
  err := enc.Encode(s.hint)
  if err != nil {
    return buf.Bytes(), err
  }

  if s.hint.ServeEmbeddings {
    err = enc.Encode(s.embeddingsServer)
    if err != nil {
      return buf.Bytes(), err
    }
  }

  if s.hint.ServeUrls {
    err = enc.Encode(s.urlsServer)
    if err != nil {
      return buf.Bytes(), err
    }
  }

  return buf.Bytes(), err
}

func (k *Coordinator) GobDecode(buf []byte) error {
  b := bytes.NewBuffer(buf)
  dec := gob.NewDecoder(b)
  err := dec.Decode(&k.numEmbServers)
  if err != nil {
    return err
  }

  err = dec.Decode(&k.embServerAddrs)
  if err != nil {
    return err
  }

  err = dec.Decode(&k.numUrlServers)
  if err != nil {
    return err
  }

  err = dec.Decode(&k.urlServerAddrs)
  if err != nil {
    return err
  }

  err = dec.Decode(&k.hint)
  if err != nil {
    return err
  }

  return nil
}

func (s *Server) GobDecode(buf []byte) error {
  b := bytes.NewBuffer(buf)
  dec := gob.NewDecoder(b)
  err := dec.Decode(&s.hint)
  if err != nil {
    return err
  }

  if s.hint.ServeEmbeddings {
    err = dec.Decode(&s.embeddingsServer)
    if err != nil {
      return err
    }
  }

  if s.hint.ServeUrls {
    err = dec.Decode(&s.urlsServer)
    if err != nil {
      return err
    }
  }

  return err
}

func DumpStateToFile[S TiptoeServer](s *S, filename string) {
  f, err := os.Create(filename) // deletes prior contents
  if err != nil {
    panic(err)
  }
  defer f.Close()

  enc := gob.NewEncoder(f)
  err = enc.Encode(s)
  if err != nil {
    panic(err)
  }
}

func LoadStateFromFile[S TiptoeServer](s *S, filename string) {
  f, err := os.Open(filename)
  if err != nil {
    panic(err)
  }
  defer f.Close()

  dec := gob.NewDecoder(f)
  err = dec.Decode(&s)
  if err != nil {
    panic(err)
  }
}
