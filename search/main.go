package main

import (
  "os"
  "fmt"
  "flag"
  "strconv"
  "runtime/pprof"
  "runtime/debug"
)

import (
  "github.com/ahenzinger/tiptoe/search/utils"
  "github.com/ahenzinger/tiptoe/search/config"
  "github.com/ahenzinger/tiptoe/search/protocol"
)

// Where the corpus is stored
var preamble = flag.String("preamble", "/home/ubuntu", "Preamble")

var hintFile = flag.String("hintfile", "", "Hint file")

// Whether or not running image search
var image_search = flag.Bool("image_search", false, "Image search")

func printUsage() {
 fmt.Println("Usage:\n\"go run . all-servers\" or\n\"go run . client coordinator-ip\" or\n\"go run . coordinator numEmbServers numUrlServers ip1 ip2 ...\" or\n\"go run . emb-server index\" or\n\"go run . url-server index\" or\n\"go run . client-latency coordinator-ip\" or\n\"go run . client-tput-embed coordinator-ip\" or\n\"go run . client-tput-url coordinator-ip\"")
}

func main() {
  coordinatorIP := "0.0.0.0"

  flag.Parse()
  args := flag.Args()

  if len(args) < 1 {
    return
  }

  conf := config.MakeConfig(*preamble + "/data/", *image_search)

  switch args[0] {
  case "client":
    if len(args) >= 2 {
      coordinatorIP = args[1]
    }

    f, _ := os.Create("client.prof")
    pprof.StartCPUProfile(f)
    defer pprof.StopCPUProfile()
  
    protocol.RunClient(utils.RemoteAddr(coordinatorIP, utils.CoordinatorPort), conf, *hintFile)
  
  case "client-latency":
    //debug.SetMemoryLimit(60 * 2^(30))
    if len(args) >= 2 {
      coordinatorIP = os.Args[1]
    }
    protocol.BenchLatency(101 /* num queries */, 
                          utils.RemoteAddr(coordinatorIP, utils.CoordinatorPort), 
			  "latency.log", conf) 
    utils.WriteFileToStdout("latency.log")

  case "client-tput-embed":
    if len(args) >= 2 {
      coordinatorIP = args[1]
    }
    protocol.BenchTputEmbed(utils.RemoteAddr(coordinatorIP, utils.CoordinatorPort), 
			    "tput_embed.log")
    utils.WriteFileToStdout("tput_embed.log")

  case "client-tput-url":
    if len(args) >= 2 {
      coordinatorIP = os.Args[1]
    }
    protocol.BenchTputUrl(utils.RemoteAddr(coordinatorIP, utils.CoordinatorPort), 
			  "tput_url.log")
    utils.WriteFileToStdout("tput_url.log")

  case "preprocess-all":
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

  case "all-servers":
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

    case "coordinator":
    numEmbServers, err1 := strconv.Atoi(args[1])
    numUrlServers, err2 := strconv.Atoi(args[2])

    if err1 != nil || err2 != nil || len(args) < 3 {
      panic("Bad input")
    }

    addrs := make([]string, numEmbServers + numUrlServers)
    for i := 0; i < numEmbServers + numUrlServers; i++ {
      ip := "0.0.0.0"
      if i+3 < len(args) {
        ip = args[i+3]
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

    case "emb-server":
    debug.SetMemoryLimit(20*2^(30)) // Necessary so don't run out of memory on r5.xlarge instances
    i, _ := strconv.Atoi(args[1])

    log := conf.EmbeddingServerLog(i)
    if !utils.FileExists(log) {
      panic("Preprocessed cluster server file does not exist")
    }

    server := protocol.NewServerFromFile(log)
    server.Serve(utils.EmbServerPortStart + i)

  case "url-server":
    debug.SetMemoryLimit(20*2^(30)) // Necessary so don't run out of memory on r5.xlarge instances
    i, _ := strconv.Atoi(args[1])

    log := conf.UrlServerLog(i)
    if !utils.FileExists(log) {
      panic("Preprocessed url server file does not exist")
    }

    server := protocol.NewServerFromFile(log)
    server.Serve(utils.UrlServerPortStart + i)
  default:
    fmt.Printf("Got unknown command: %v", args[0])
    printUsage()
  }
}
