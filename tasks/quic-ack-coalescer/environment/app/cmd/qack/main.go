package main

import (
	"fmt"
	"os"

	"qack/internal/report"
)

func main() {
	dataDir := os.Getenv("QACK_DATA_DIR")
	if dataDir == "" {
		dataDir = "/app/ack_trove"
	}
	outDir := os.Getenv("QACK_OUT_DIR")
	if outDir == "" {
		outDir = "/app/output"
	}
	if err := report.Run(dataDir, outDir); err != nil {
		fmt.Fprintf(os.Stderr, "qack: %v\n", err)
		os.Exit(1)
	}
}
