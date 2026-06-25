package main

import (
	"flag"
	"fmt"
	"os"

	"vendorlab/internal/app"
	"vendorlab/internal/ingest"
	reportio "vendorlab/internal/io"
)

func main() {
	configPath := flag.String("config", "", "profile JSON path")
	outPath := flag.String("out", "", "output JSON path")
	flag.Parse()
	if *configPath == "" || *outPath == "" {
		fmt.Fprintln(os.Stderr, "usage: vendorlab --config <path> --out <path>")
		os.Exit(2)
	}
	data, err := os.ReadFile(*configPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	cfg, err := app.ParseConfig(data)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	report, err := ingest.Run("/app/environment", cfg)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := reportio.WriteReport(*outPath, report); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
