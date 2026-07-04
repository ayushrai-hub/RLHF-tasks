package main

import (
	"flag"
	"fmt"
	"os"

	"offline-search-shard-coherence/internal/search"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: offline-search search --plan PLAN --out OUT")
		os.Exit(2)
	}
	switch os.Args[1] {
	case "search":
		fs := flag.NewFlagSet("search", flag.ExitOnError)
		planPath := fs.String("plan", "", "plan JSON path")
		outPath := fs.String("out", "", "output JSON path")
		_ = fs.Parse(os.Args[2:])
		if *planPath == "" || *outPath == "" {
			fmt.Fprintln(os.Stderr, "search requires --plan and --out")
			os.Exit(2)
		}
		if err := search.Run(*planPath, *outPath); err != nil {
			fmt.Fprintf(os.Stderr, "offline-search: %v\n", err)
			os.Exit(1)
		}
	default:
		fmt.Fprintf(os.Stderr, "unknown command %q\n", os.Args[1])
		os.Exit(2)
	}
}
