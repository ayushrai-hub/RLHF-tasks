
package main

import (
  "flag"
  "fmt"
  "os"
  "strings"

  "gradlab/internal/ingest"
  "gradlab/internal/pipeline"
)

func main() {
  set := flag.String("set", "", "graph set")
  graphs := flag.String("graphs", "", "comma graph names")
  reset := flag.Bool("reset", false, "reset var state")
  flag.Parse()
  var names []string
  switch {
  case *graphs != "":
    names = strings.Split(*graphs, ",")
  case *set != "":
    names = ingest.SetMap[*set]
  default:
    names = ingest.SetMap["all"]
  }
  if err := pipeline.RunNames(names, *reset); err != nil {
    fmt.Fprintln(os.Stderr, err)
    os.Exit(1)
  }
}
