package main



import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/terminal-bench/splitter/config"
	"github.com/terminal-bench/splitter/models"
	"github.com/terminal-bench/splitter/splitter"
)

const (
	configPath  = "/app/environment/config/split_rules.json"
	requestsPath = "/app/environment/data/requests.json"
	outputPath  = "/app/output/routing_result.json"
)

func main() {
	cfg, err := config.LoadConfig(configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error loading config: %v\n", err)
		os.Exit(1)
	}

	reqs, err := config.LoadRequests(requestsPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error loading requests: %v\n", err)
		os.Exit(1)
	}

	var seed int64
	if envSeed := os.Getenv("SEED"); envSeed != "" {
		if parsed, err := strconv.ParseInt(envSeed, 10, 64); err == nil {
			seed = parsed
		} else {
			seed = time.Now().UnixNano()
		}
	} else {
		seed = time.Now().UnixNano()
	}
	results, summary := splitter.RouteRequests(reqs, cfg, seed)

	report := models.OutputReport{
		RoutedRequests: results,
		Summary:        *summary,
	}

	out, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "error marshaling output: %v\n", err)
		os.Exit(1)
	}

	if err := os.WriteFile(outputPath, out, 0644); err != nil {
		fmt.Fprintf(os.Stderr, "error writing output: %v\n", err)
		os.Exit(1)
	}
}
