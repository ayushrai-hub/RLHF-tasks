package main

import (
	"flag"
	"fmt"
	"os"

	"example.com/fleetrisk/internal/app"
)

func main() {
	var opts app.Options
	flag.StringVar(&opts.ModelPath, "model", "/app/config/model.json", "path to model config")
	flag.StringVar(&opts.PolicyPath, "policy", "/app/config/policy.json", "path to policy config")
	flag.StringVar(&opts.CallsPath, "calls", "/app/data/service_calls.csv", "path to service calls CSV")
	flag.StringVar(&opts.WindowsPath, "windows", "/app/data/sensor_windows.csv", "path to sensor windows CSV")
	flag.StringVar(&opts.HistoryPath, "history", "/app/data/asset_history.csv", "path to asset history CSV")
	flag.StringVar(&opts.LabelsPath, "labels", "/app/data/maintenance_labels.csv", "path to labels CSV")
	flag.StringVar(&opts.CapacityPath, "capacity", "/app/data/site_capacity.csv", "path to site capacity CSV")
	flag.StringVar(&opts.OutDir, "out-dir", "/app/out", "output directory")
	flag.Parse()

	if err := app.Run(opts); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: %v\n", err)
		os.Exit(1)
	}
}
