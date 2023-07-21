package utils

import (
  "os"
  "fmt"
  "bufio"
)

func OpenFile(file string) *os.File {
  f, err := os.Open(file)
  if err != nil {
    fmt.Println(err)
    panic("Error opening file")
  }
  return f
}

func OpenAppendFile(file string) *os.File {
  f, err := os.OpenFile(file, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
  if err != nil {
    fmt.Println(err)
    panic("Error opening file")
  }
  return f
}

func FileExists(file string) bool {
  if _, err := os.Stat(file); err != nil {
    return false
  }
  return true
}

func AllFilesExist(files []string) bool {
  for _, f := range files {
    if !FileExists(f) {
      return false
    }
  }
  return true
}

func ReadFromChannel(ch chan bool, num int, verbose bool) {
  for i := 0; i < num; i++ {
    d := <- ch
    if verbose {
      fmt.Printf("   %d of %d tasks finished\n", i, num)
    }
    if !d {
      panic("Should not happen!")
    }
  }
}

func WriteFileToStdout(file string) {
  data, err := os.ReadFile(file)

  if err != nil {
    fmt.Println(file)
    panic("Error reading file")
  }

  os.Stdout.Write(data)
}

func ReadLineFromStdin() string {
  in := bufio.NewScanner(os.Stdin)
  in.Scan()
  return in.Text()
}
