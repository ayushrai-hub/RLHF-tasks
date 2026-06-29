package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"pathfb/batchrun"
)

func main() {
	scenariosDir := flag.String("scenarios-dir", "", "directory containing JSON pack fixtures")
	output := flag.String("out", "", "path for regenerated path failback report JSON")
	flag.Parse()
	if *scenariosDir == "" || *output == "" {
		fmt.Fprintln(os.Stderr, "usage: pathfb-sweep --scenarios-dir DIR --out PATH")
		os.Exit(2)
	}
	env, err := batchrun.RunAll(*scenariosDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	out, err := json.MarshalIndent(env, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	out = append(out, '\n')
	if err := os.WriteFile(*output, out, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
