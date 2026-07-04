package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	dossier := flag.String("dossier", "", "path to governance dossier markdown")
	configDir := flag.String("config-dir", "", "directory of input YAML/TOML configs")
	outDir := flag.String("out-dir", "", "directory for hardened configs")
	evidence := flag.String("evidence", "", "path to SQLite evidence database")
	flag.Parse()

	if *dossier == "" || *configDir == "" || *outDir == "" || *evidence == "" {
		fmt.Fprintln(os.Stderr, "all flags required: --dossier --config-dir --out-dir --evidence")
		os.Exit(2)
	}

	if err := run(*dossier, *configDir, *outDir, *evidence); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
