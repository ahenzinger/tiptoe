package protocol

import (
  "flag"
  "testing"
  "runtime/debug"
)

import (
  "github.com/ahenzinger/tiptoe/search/utils"
  "github.com/ahenzinger/tiptoe/search/config"
)

var medcorpus = flag.String("medcorpus", "../corpus/medcorpus.csv", "Synthetic test corpus")
var preamble = flag.String("preamble", "/home/ubuntu", "Preamble where the real corpus is stored")

var k *Coordinator
var s *Server
var s2 *Server

var serverTcp = utils.LocalAddr(utils.ServerPort)
var server2Tcp = utils.LocalAddr(utils.ServerPort2)
var coordinatorTcp = utils.LocalAddr(utils.CoordinatorPort)

var conf *config.Config

// Client talks to servers over TCP, to coordinator over TLS
func TestMain(m *testing.M) {
  s = serverInit()
  s2 = serverInit()
  k = coordinatorInit()

  go s.Serve(utils.ServerPort)
  go s2.Serve(utils.ServerPort2)
  go k.Serve(utils.CoordinatorPort)

  conf = config.MakeConfig(*preamble + "/data/", false /* image search */)

  debug.SetMemoryLimit(28 * 2^(30)) // 28 GiB of RAM
  m.Run()
}
