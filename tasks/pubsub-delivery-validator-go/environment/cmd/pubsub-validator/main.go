package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"pubsub-validator/pkg/config"
	"pubsub-validator/pkg/parser"
	"pubsub-validator/pkg/report"
	"pubsub-validator/pkg/validator"
)

func main() {
	dataPath := flag.String("data", "/app/data/delivery_log.json", "delivery log")
	configPath := flag.String("config", "/app/config/pubsub.toml", "config")
	outputDir := flag.String("output", "/app/output", "output directory")
	flag.Parse()

	cfg := config.LoadConfig(*configPath)
	log := parser.LoadDeliveryLog(*dataPath)
	result := validator.Validate(log, cfg)
	r := report.Generate(result, cfg, log)

	os.MkdirAll(*outputDir, 0755)
	out, _ := json.MarshalIndent(r, "", "  ")
	os.WriteFile(filepath.Join(*outputDir, "results.json"), out, 0644)
	fmt.Println("Validation complete")
}
