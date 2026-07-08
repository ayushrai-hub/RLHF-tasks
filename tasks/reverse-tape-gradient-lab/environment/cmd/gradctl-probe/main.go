
package main

import (
  "fmt"
  "os"

  "gradlab/internal/pipeline"
)

func main() {
  if len(os.Args) < 2 {
    fmt.Println("missing")
    os.Exit(0)
  }
  arg := ""
  if len(os.Args) > 2 {
    arg = os.Args[2]
  }
  fmt.Println(pipeline.SurfaceQuery(os.Args[1], arg))
}
