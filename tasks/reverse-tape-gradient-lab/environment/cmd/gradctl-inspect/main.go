
package main

import (
  "encoding/json"
  "fmt"
  "os"
  "strings"

  "gradlab/internal/paths"
)

func main() {
  sb, err := os.ReadFile(paths.SessionPath)
  if err != nil {
    fmt.Println("missing")
    return
  }
  var sess map[string]any
  _ = json.Unmarshal(sb, &sess)
  labels := []string{}
  if arr, ok := sess["graph_labels"].([]any); ok {
    for _, x := range arr {
      labels = append(labels, x.(string))
    }
  }
	fmt.Printf("run_count=%v epoch=%v fingerprint=%v graphs=%s\n",
		sess["run_count"], readEpoch(), sess["last_fingerprint"], strings.Join(labels, ","))
}

func readEpoch() any {
  b, err := os.ReadFile(paths.EpochPath)
  if err != nil {
    return 1
  }
  var e map[string]any
  _ = json.Unmarshal(b, &e)
  return e["current"]
}
