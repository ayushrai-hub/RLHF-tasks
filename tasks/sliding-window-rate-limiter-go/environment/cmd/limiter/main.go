package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"sliding-window-limiter/internal/config"
	"sliding-window-limiter/internal/loader"
	"sliding-window-limiter/internal/ratelimit"
	"sliding-window-limiter/internal/reporter"
)

func main() {
	if len(os.Args) < 2 || os.Args[1] != "analyze" {
		fmt.Fprintf(os.Stderr, "Usage: rate-limiter analyze --traffic <path> --output <path> --format <json|text|both>\n")
		os.Exit(1)
	}
	var trafficPath, outputPath, format string
	for i := 2; i < len(os.Args); i++ {
		switch os.Args[i] {
		case "--traffic":
			i++
			if i < len(os.Args) { trafficPath = os.Args[i] }
		case "--output":
			i++
			if i < len(os.Args) { outputPath = os.Args[i] }
		case "--format":
			i++
			if i < len(os.Args) { format = os.Args[i] }
		}
	}
	if trafficPath == "" || outputPath == "" {
		fmt.Fprintf(os.Stderr, "--traffic and --output are required\n")
		os.Exit(1)
	}
	if format == "" { format = "both" }

	cfg := config.Load("/app/config")
	requests, err := loader.LoadTraffic(trafficPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	result := ratelimit.Analyze(requests, cfg)
	os.MkdirAll(outputPath, 0755)
	if format == "json" || format == "both" {
		data, _ := json.MarshalIndent(result, "", "  ")
		os.WriteFile(filepath.Join(outputPath, "limiter_report.json"), data, 0644)
	}
	if format == "text" || format == "both" {
		text := reporter.FormatText(result)
		os.WriteFile(filepath.Join(outputPath, "limiter_report.txt"), []byte(text), 0644)
	}
}
