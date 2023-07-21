// Taken from: https://github.com/henrycg/prio/blob/master/utils/rpc.go
// and https://github.com/henrycg/sbmozilla/blob/main/sbserver/server.go

package utils

import (
  "fmt"
  "net"
  "strconv"
  "net/rpc"
  "crypto/tls"
)

var publicKey = `-----BEGIN CERTIFICATE-----
MIIBVTCB/KADAgECAgEAMAoGCCqGSM49BAMCMBIxEDAOBgNVBAoTB0FjbWUgQ28w
HhcNMTQwNTAyMDQ0NDM4WhcNMTUwNTAyMDQ0NDM4WjASMRAwDgYDVQQKEwdBY21l
IENvMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEU7EtIv3GVZKMduiOwmQBzrqI
XnF84tNhcPSNtnw8cTgF8CPfJ0wcCbIvgQXEeZpTgn+A5N7YpdooUiwtICadeKND
MEEwDgYDVR0PAQH/BAQDAgCgMBMGA1UdJQQMMAoGCCsGAQUFBwMBMAwGA1UdEwEB
/wQCMAAwDAYDVR0RBAUwA4IBKjAKBggqhkjOPQQDAgNIADBFAiBU0cZRnenXWw0Y
OgQekAT+sx64ptjzm+ruABzBcIggbQIhAL2XbTx1l8IgmxtQZnK5S9wUmiIYMSxz
F2OaCRUekyth
-----END CERTIFICATE-----
`

var privateKey = `
-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIKbLcggTNozKjPjKdF2ZL/cT1i0UnT2gkcSi+sqxBebioAoGCCqGSM49
AwEHoUQDQgAEU7EtIv3GVZKMduiOwmQBzrqIXnF84tNhcPSNtnw8cTgF8CPfJ0wc
CbIvgQXEeZpTgn+A5N7YpdooUiwtICadeA==
-----END EC PRIVATE KEY-----
`
const (
  ServerPort = 1234
  ServerPort2 = 1235
  CoordinatorPort = 1237

  EmbServerPortStart = 1240
  UrlServerPortStart = 1450
)

func LocalAddr(port int) string {
  return localIP().String() + ":" + strconv.Itoa(port)
}

func RemoteAddr(ip string, port int) string {
  return ip + ":" + strconv.Itoa(port)
}

func localIP() net.IP {
  addrs, err := net.InterfaceAddrs()
  if err != nil {
    fmt.Println(err)
    panic("Error looking up own IP")
  }

  for _, addr := range addrs {
    if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
      if ipnet.IP.To4() != nil {
        return ipnet.IP
      }
    }
  }

  panic("Own IP not found")
  return nil
}

/*
 * callTLS and callTCP send an RPC to the server; then wait for the response.
 */
func DialTLS(address string) *rpc.Client {
  var config tls.Config
  config.InsecureSkipVerify = true

  conn, err := tls.Dial("tcp", address, &config)
  if err != nil {
    panic(err)
    panic("Should not happen")
  }

  return rpc.NewClient(conn)
}

func CallTLS(c *rpc.Client, rpcname string, args interface{}, reply interface{}) {
  err := c.Call(rpcname, args, reply)
  if err == nil {
    return 
  }

  fmt.Printf("Err: %s\n", err)
  panic("Call failed")
}

func DialTCP(addr string) *rpc.Client {
  c, err := rpc.Dial("tcp", addr)

  if err != nil {
    fmt.Printf("Tried to dial %s\n", addr)
    fmt.Printf("DialHTTP error: %s\n", err)
    panic("Dialing error")
  }

  return c
}

func CallTCP(c *rpc.Client, rpcname string, args interface{}, reply interface{}) {
  err := c.Call(rpcname, args, reply)
  if err == nil {
    return 
  }

  fmt.Printf("Err: %s\n", err)
  panic("Call failed")
}

/*
 * serveTLS and serveTCP implement the server-side networking logic.
 */
func ListenAndServeTCP(server *rpc.Server, port int) {
  address := LocalAddr(port)
  l, err := net.Listen("tcp", address)
  if err != nil {
    fmt.Printf("Listener error: %v\n", err)
    panic("Listener error")
  }

  defer l.Close()

  fmt.Printf("TCP server listening on %s\n", address)
  for {
    conn, err := l.Accept()
    if err != nil {
      fmt.Printf("Listener error: %v\n", err)
      continue
    }

    defer conn.Close()
    go server.ServeConn(conn)
  }
}

func ListenAndServeTLS(server *rpc.Server, port int) {
  address := LocalAddr(port)
  cert, err := tls.X509KeyPair([]byte(publicKey), []byte(privateKey))
  if err != nil {
    fmt.Printf("Could not load certficate: %v\n", err)
    panic("Could not load certificate")
  }

  var config tls.Config
  config.InsecureSkipVerify = true
  config.Certificates = []tls.Certificate{cert}

  l, err := tls.Listen("tcp", address, &config)
  if err != nil {
    fmt.Printf("Listener error: %v\n", err)
    panic("Listener error")
  }

  defer l.Close()

  fmt.Printf("TLS server listening on %s\n", address)
  for {
    conn, err := l.Accept()
    if err != nil {
      fmt.Printf("Listener error: %v\n", err)
      continue
    }

    go handleOneClientTLS(conn, server)
  }
}

func handleOneClientTLS(conn net.Conn, server *rpc.Server) {
  defer conn.Close()

  tlscon, ok := conn.(*tls.Conn)
  if !ok {
    fmt.Println("Could not cast conn")
    return
  }

  err := tlscon.Handshake()
  if err != nil {
    fmt.Printf("Handshake failed: %v\n", err)
    return
  }
  fmt.Println("Handshake OK")

  server.ServeConn(conn)
}
