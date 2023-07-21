package config

import (
  "math"
)

type Config struct {
  preamble    string
  imageSearch bool
}

func MakeConfig(preambleStr string, images bool) *Config {
  c := Config{
	preamble: preambleStr,
	imageSearch: images,
  }
  return &c
}

func (c *Config) PREAMBLE() string {
  return c.preamble
}

func (c *Config) IMAGE_SEARCH() bool {
  return c.imageSearch
}

// TODO: Fix to be more accurate
func (c *Config) DEFAULT_EMBEDDINGS_HINT_SZ() uint64 {
  if !c.imageSearch {
    return 500
  } else {
    return 900
  }
}

func DEFAULT_URL_HINT_SZ() uint64 {
  return 100
}

func (c *Config) EMBEDDINGS_DIM() uint64 {
  if !c.imageSearch {
    return 192
  } else {
    return 384
  }
}

func SLOT_BITS() uint64 {
  return 5
}

func (c *Config) TOTAL_NUM_CLUSTERS() int {
  if !c.imageSearch {
    return 25196
  } else {
    return 42528
  }
}

// Round up (# clusters / # embedding servers)
func (c *Config) EMBEDDINGS_CLUSTERS_PER_SERVER() int {
  clustersPerServer := float64(c.TOTAL_NUM_CLUSTERS()) / float64(c.MAX_EMBEDDINGS_SERVERS())
  return int(math.Ceil(clustersPerServer))
}

func (c *Config) MAX_EMBEDDINGS_SERVERS() int {
  if !c.imageSearch {
    return 80
  } else {
    return 160
  }
}

// Round up (# clusters / # url servers)
func (c *Config) URL_CLUSTERS_PER_SERVER() int {
  clustersPerServer := float64(c.TOTAL_NUM_CLUSTERS()) / float64(c.MAX_URL_SERVERS())
  return int(math.Ceil(clustersPerServer))
}

func (c *Config) MAX_URL_SERVERS() int {
  if !c.imageSearch {
    return 8
  } else {
    return 16
  }
}

func (c *Config) SIMPLEPIR_EMBEDDINGS_RECORD_LENGTH() int {
  if !c.imageSearch {
    return 17
  } else {
    return 15
  }
}
