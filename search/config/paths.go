package config

import (
  "fmt"
)

func (c *Config) TxtCorpus(clusterId int) string {
  return fmt.Sprintf("%s/clusters/cluster_%d.txt", 
                     c.preamble, 
		     clusterId)
}

func (c *Config) EmbeddingServerLog(serverId int) string {
  return fmt.Sprintf("%s/artifact/dim%d/cluster-server-%d.log", 
                     c.preamble, 
		     c.EMBEDDINGS_DIM(), 
		     serverId)
}

func (c *Config) UrlServerLog(serverId int) string {
  return fmt.Sprintf("%s/artifact/dim%d/url-server-%d.log",
                     c.preamble,
		     c.EMBEDDINGS_DIM(), 
		     serverId)
}

func (c *Config) CoordinatorLog(numEmbServers, numUrlServers int) string {
  return fmt.Sprintf("%s/artifact/dim%d/coordinator-%d-%d.log", 
                     c.preamble,
		     c.EMBEDDINGS_DIM(), 
		     numEmbServers, 
		     numUrlServers)
}

func (c *Config) EmbeddingServerLogWithoutHint(serverId int) string {
  return fmt.Sprintf("%s/artifact/dim%d/cluster-server-no-hint-%d.log",
                     c.preamble,
		     c.EMBEDDINGS_DIM(),
		     serverId)
}

func (c *Config) UrlServerLogWithoutHint(serverId int) string {
  return fmt.Sprintf("%s/artifact/dim%d/url-server-no-hint-%d.log",
                     c.preamble,
 		     c.EMBEDDINGS_DIM(),
 		     serverId)
}
