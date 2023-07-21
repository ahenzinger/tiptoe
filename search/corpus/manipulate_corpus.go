package corpus


func Concat(arr []*Corpus) *Corpus {
  if len(arr) == 0 {
    return nil
  }

  c := arr[0].copyCorpus()
  for _, e := range arr[1:] {
    c.concat(e)
  }

  return c
}

func (c *Corpus) copyCorpus() *Corpus {
  r := new(Corpus)
  r.params = c.params

  r.embeddings = make([]int8, len(c.embeddings))
  copy(r.embeddings[:], c.embeddings[:])

  r.urls = make([][]byte, len(c.urls))
  for i, v := range c.urls {
    r.urls[i] = make([]byte, len(v))
    copy(r.urls[i][:], v[:])
  }

  r.embeddingsClusterMap = make(map[uint]uint)
  for k, v := range c.embeddingsClusterMap {
    r.embeddingsClusterMap[k] = v
  }

  r.urlClusterMap = make(map[uint][]Subcluster)
  for k, v := range c.urlClusterMap {
    v2 := make([]Subcluster, len(v))
    copy(v2[:], v[:]) 
    r.urlClusterMap[k] = v2
  }

  r.maxClusterId = c.maxClusterId
  return r
}

func (c1 *Corpus) concat(c2 *Corpus) {
  if c1.params.NumDocs == 0 || c2.params.NumDocs == 0 {
    panic("Corpus is empty")
  }

  if !c1.params.Consistent(&c2.params) {
    panic("Corpus parameters do not match")
  }

  if (len(c1.embeddings) == 0 && len(c2.embeddings) > 0) ||
     (len(c1.urls) == 0 && len(c2.urls) > 0) ||
     (len(c1.embeddings) > 0 && len(c2.embeddings) == 0) ||
     (len(c1.urls) > 0 && len(c2.urls) == 0) {
    panic("Should not happen")
  }

  c1.params.NumDocs += c2.params.NumDocs

  if len(c1.embeddings) > 0 {
    offset := uint(len(c1.embeddings))
    c1.embeddings = append(c1.embeddings, c2.embeddings...)

    for k, v := range c2.embeddingsClusterMap {
      if _, ok := c1.embeddingsClusterMap[k]; ok {
        panic("Key should not be present")
      }
      c1.embeddingsClusterMap[k] = v + offset
    }
  }

  if len(c1.urls) > 0 {
    offset := uint64(len(c1.urls))
    c1.urls = append(c1.urls, c2.urls...)

    for k, v := range c2.urlClusterMap {
      if _, ok := c1.urlClusterMap[k]; ok {
        panic("Key should not be present")
      }

      c1.urlClusterMap[k] = make([]Subcluster, len(v))
      for i, val := range v {
        c1.urlClusterMap[k][i] = val
        c1.urlClusterMap[k][i].index += offset
      }
    }

    if c1.params.UrlBytes < c2.params.UrlBytes {
      c1.params.UrlBytes = c2.params.UrlBytes
    }
  }

  if c2.maxClusterId > c1.maxClusterId {
    c1.maxClusterId = c2.maxClusterId
  }
}
