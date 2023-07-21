package corpus

import (
  "os"
  "fmt"
  "bytes"
  "errors"
  "strings"
  "strconv"
  "io/ioutil"
  "encoding/csv"
  "compress/zlib"
)

const (
  SUBCLUSTER_DELIM = "-------------------------"
  URL_DELIM = " "

  MAX_URL_LEN = 500
  DISALLOW_EMPTY_CLUSTERS = false
)

func Compress(s string) []byte {
  var buf bytes.Buffer
  zw, err := zlib.NewWriterLevel(&buf, zlib.BestCompression)

  _, err2 := zw.Write([]byte(s))
  if err != nil || err2 != nil {
    fmt.Printf("%s %s\n", err, err2)
    panic("Error with zlib")
  }

  zw.Close()
  return buf.Bytes()
}

func Decompress(b []byte) (string, error) {
  r := bytes.NewReader(b)
  zr, err := zlib.NewReader(r)
  if err != nil {
    fmt.Println(err)
    return "", err
  }
  defer zr.Close()

  data, err := ioutil.ReadAll(zr)
  if (err != nil) {
    fmt.Println(err)
    return "", err
  }

  if string(data) == "" {
    panic("Gzip should not recover empty string")
    return "", errors.New("Gzip returned empty string")
  }

  return strings.TrimRight(string(data), "\x00"), nil
}

func parseCsvHeader(f *os.File) (*csv.Reader, uint64, uint64, uint64) {
  reader := csv.NewReader(f)

  line1, err1 := reader.Read()
  line2, err2 := reader.Read()
  line3, err3 := reader.Read()
  if (err1 != nil) || (err2 != nil) || (err3 != nil) {
    panic("Error reading CSV header")
  }

  numDocs, err1 := strconv.Atoi(line1[0])
  embeddingSlots, err2 := strconv.Atoi(line2[0])
  slotBits, err3 := strconv.Atoi(line3[0])
  if (err1 != nil) || (err2 != nil) || (err3 != nil) {
    panic("Error parsing CSV header")
  }

  return reader, uint64(numDocs), uint64(embeddingSlots), uint64(slotBits)
}

func parseDelimitersTxt(txt string) (int, int) {
  i1 := strings.Index(txt, "|")
  if i1 == -1 {
    fmt.Println(txt)
    fmt.Println(i1)
    panic("Should not happen")
  }
  
  txt = txt[i1 + 2:]
  i2 := strings.Index(txt, "|")
  if i2 == -1 {
    fmt.Println(txt)
    fmt.Println(i2)
    panic("Should not happen")
  }

  return i1, i1 + 2 + i2
}

func parseEmbeddingsTxt(txt string) []string {
  i1, i2 := parseDelimitersTxt(txt)
  return strings.Split(txt[i1 + 2 : i2 - 1], ",")
}

func parseUrlTxt(txt string) string {
  _, i := parseDelimitersTxt(txt)
  return strings.Trim(txt[i + 2:], " ")
}

func GetIthUrl(strs string, num uint64) string {
  for i := uint64(0); i < num; i++ {
    index := strings.Index(strs, URL_DELIM)
    if index == -1 {
      fmt.Println(strs)
      fmt.Printf("Only matched %d delimiters -- wanted %d\n", i, num)
      panic("Should not happen")
    }
    strs = strs[index+1:]
  }

  index := strings.Index(strs, URL_DELIM)
  if index == -1 {
    return strs
  }

  return strs[:index]
}

func CountUrls(s string) int {
  index := strings.Index(s, URL_DELIM)
  if index == -1 {
    return 1
  }
  return 1 + CountUrls(s[index+1:])
}
