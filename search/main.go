package main

import (
  "os"
  "fmt"
  "flag"
  "strconv"
  "runtime/debug"
)

import (
  "github.com/ahenzinger/tiptoe/search/utils"
  "github.com/ahenzinger/tiptoe/search/config"
  "github.com/ahenzinger/tiptoe/search/protocol"
)

// Where the corpus is stored
var preamble = flag.String("preamble", "/home/ubuntu", "Preamble")

// Whether or not running image search
var image_search = flag.Bool("image_search", false, "Image search")

func printUsage() {
 fmt.Println("Usage:\n\"go run . all-servers\" or\n\"go run . client coordinator-ip\" or\n\"go run . coordinator numEmbServers numUrlServers ip1 ip2 ...\" or\n\"go run . emb-server index\" or\n\"go run . url-server index\" or\n\"go run . client-latency coordinator-ip\" or\n\"go run . client-tput-embed coordinator-ip\" or\n\"go run . client-tput-url coordinator-ip\" or\n\"go run . client-tput-offline coordinator-ip\"")
}

func main() {
  coordinatorIP := "0.0.0.0"
  if len(os.Args) < 2 {
    return
  }

  conf := config.MakeConfig(*preamble + "/data/", *image_search)

  if os.Args[1] == "client" {
    if len(os.Args) >= 3 {
      coordinatorIP = os.Args[2]
    }

    protocol.RunClient(utils.RemoteAddr(coordinatorIP, utils.CoordinatorPort), conf)

  } else if os.Args[1] == "client-latency" {
    debug.SetMemoryLimit(20 * 2^(30))
    if len(os.Args) >= 3 {
      coordinatorIP = os.Args[2]
    }
    protocol.BenchLatency(101 /* num queries */,
                          utils.RemoteAddr(coordinatorIP, utils.CoordinatorPort),
			  "latency.log", conf)
    utils.WriteFileToStdout("latency.log")

  } else if os.Args[1] == "client-tput-embed" {
    if len(os.Args) >= 3 {
      coordinatorIP = os.Args[2]
    }
    protocol.BenchTputEmbed(utils.RemoteAddr(coordinatorIP, utils.CoordinatorPort),
			    "tput_embed.log")
    utils.WriteFileToStdout("tput_embed.log")

  } else if os.Args[1] == "client-tput-url" {
    if len(os.Args) >= 3 {
      coordinatorIP = os.Args[2]
    }
    protocol.BenchTputUrl(utils.RemoteAddr(coordinatorIP, utils.CoordinatorPort),
			  "tput_url.log")
    utils.WriteFileToStdout("tput_url.log")

  } else if os.Args[1] == "client-tput-offline" {
    if len(os.Args) >= 3 {
      coordinatorIP = os.Args[2]
    }
    protocol.BenchTputOffline(utils.RemoteAddr(coordinatorIP, utils.CoordinatorPort),
			      "tput_offline.log")
    utils.WriteFileToStdout("tput_offline.log")
    
  } else if os.Args[1] == "preprocess-all" {
    //debug.SetMemoryLimit(700 * 2^(30))
    protocol.NewEmbeddingServers(0,
                                 conf.MAX_EMBEDDINGS_SERVERS(),
                                 conf.EMBEDDINGS_CLUSTERS_PER_SERVER(),
			         conf.DEFAULT_EMBEDDINGS_HINT_SZ(),
				 true,  // log
				 false, // wantCorpus
				 false, // serve
				 conf)
    fmt.Println("Set up all embedding servers")

    protocol.NewUrlServers(conf.MAX_URL_SERVERS(),
                           conf.URL_CLUSTERS_PER_SERVER(),
		  	   config.DEFAULT_URL_HINT_SZ(),
			   true,  // log
			   false, // wantCorpus
			   false, // serve
			   conf)
    fmt.Println("Set up all url servers")

  } else if os.Args[1] == "preprocess-coordinator" {
    debug.SetMemoryLimit(200 * 2^(30))
    protocol.LocalSetupCoordinator(conf)

  } else if os.Args[1] == "all-servers" {
    debug.SetMemoryLimit(700 * 2^(30))
    _, embAddrs, _ := protocol.NewEmbeddingServers(0,
                                                   conf.MAX_EMBEDDINGS_SERVERS(),
                                                   conf.EMBEDDINGS_CLUSTERS_PER_SERVER(),
			   	                   conf.DEFAULT_EMBEDDINGS_HINT_SZ(),
				                   true,  // log
				                   false, // wantCorpus
						   true,  // serve
						   conf)
    fmt.Println("Set up all embedding servers")

    _, urlAddrs, _ := protocol.NewUrlServers(conf.MAX_URL_SERVERS(),
                                             conf.URL_CLUSTERS_PER_SERVER(),
					     config.DEFAULT_URL_HINT_SZ(),
					     true,  // log
					     false, // wantCorpus
					     true,  // serve
					     conf)
    fmt.Println("Set up all url servers")

    protocol.RunCoordinator(conf.MAX_EMBEDDINGS_SERVERS(),
  		            conf.MAX_URL_SERVERS(),
		            utils.CoordinatorPort,
		            append(embAddrs, urlAddrs...),
	                    true, // log
			    conf)

  } else if os.Args[1] == "coordinator" {
    numEmbServers, err1 := strconv.Atoi(os.Args[2])
    numUrlServers, err2 := strconv.Atoi(os.Args[3])

    if err1 != nil || err2 != nil || len(os.Args) < 4 {
      panic("Bad input")
    }

    addrs := make([]string, numEmbServers + numUrlServers)
    for i := 0; i < numEmbServers + numUrlServers; i++ {
      ip := "0.0.0.0"
      if i+4 < len(os.Args) {
        ip = os.Args[i+4]
      }

      if i < numEmbServers {
        addrs[i] = utils.RemoteAddr(ip, utils.EmbServerPortStart + i)
      } else {
        addrs[i] = utils.RemoteAddr(ip, utils.UrlServerPortStart + i - numEmbServers)
      }
    }

    protocol.RunCoordinator(numEmbServers,
                            numUrlServers,
		            utils.CoordinatorPort,
		            addrs,
		            true, // log
			    conf)

  } else if os.Args[1] == "build-logs-without-hint" {
    debug.SetMemoryLimit(700*2^(30))

    ch := make(chan bool)
    for i := 0; i < conf.MAX_EMBEDDINGS_SERVERS(); i += 20 {
      fmt.Printf("Embedding servers: %d\n", i)
      for j := 0; j < 20; j++ {
        go func(at int) {
          log := conf.EmbeddingServerLog(at)
          logNoHint := conf.EmbeddingServerLogWithoutHint(at)

          if !utils.FileExists(log) {
            panic("Preprocessed cluster server file does not exist")
          }

          server := protocol.NewServerFromFile(log)
          protocol.DumpServerToFileWithoutHint(server, logNoHint)
	  ch <- true
	}(i + j)
      }

      for j := 0; j < 20; j++ {
        <-ch
      }
    }

    for i := 0; i < conf.MAX_URL_SERVERS(); i++ {
      go func(at int) {
        fmt.Printf("URL servers: %d\n", at)
        log := conf.UrlServerLog(at)
        logNoHint := conf.UrlServerLogWithoutHint(at)

        if !utils.FileExists(log) {
          panic("Preprocessed url server file does not exist")
        }

        server := protocol.NewServerFromFile(log)
        protocol.DumpServerToFileWithoutHint(server, logNoHint)
	ch <- true
      }(i)
    }

    for i := 0; i < conf.MAX_URL_SERVERS(); i++ {
      <- ch
    }

  } else if os.Args[1] == "emb-server" {
    debug.SetMemoryLimit(25*2^(30)) // Necessary so don't run out of memory on r5.xlarge instances
    i, _ := strconv.Atoi(os.Args[2])

    var log string
    if *image_search {
      log = conf.EmbeddingServerLogWithoutHint(i)
    } else {
      log = conf.EmbeddingServerLog(i)
    }
    if !utils.FileExists(log) {
      panic("Preprocessed cluster server file does not exist")
    }

    var server *protocol.Server
    if *image_search {
      server = protocol.NewServerFromFileWithoutHint(log)
    } else {
      server = protocol.NewServerFromFile(log)
    }
    server.Serve(utils.EmbServerPortStart + i)

  } else if os.Args[1] == "url-server" {
    debug.SetMemoryLimit(25*2^(30)) // Necessary so don't run out of memory on r5.xlarge instances
    i, _ := strconv.Atoi(os.Args[2])

    var log string
    if *image_search {
      log = conf.UrlServerLogWithoutHint(i)
    } else {
      log = conf.UrlServerLog(i)
    }
    if !utils.FileExists(log) {
      panic("Preprocessed url server file does not exist")
    }

    var server *protocol.Server
    if *image_search {
      server = protocol.NewServerFromFileWithoutHint(log)
    } else {
      server = protocol.NewServerFromFile(log)
    }
    server.Serve(utils.UrlServerPortStart + i)

  } else {
    printUsage()
  }
}
