package main

import (
	"encoding/json"
	"fmt"
	"os"

	"docker-network-connectivity-debugger/internal/docker_network_connectivity_debugger_capture"
	"docker-network-connectivity-debugger/internal/docker_network_connectivity_debugger_replay"
)

type manifest struct {
	Scenarios []string `json:"scenarios"`
}

func main() {
	dataDir := "/app/data"
	manifestPath := dataDir + "/docker_network_connectivity_debugger_manifest.json"
	outPath := "/app/build/docker_network_connectivity_debugger_report.json"

	raw, err := os.ReadFile(manifestPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "read manifest: %v\n", err)
		os.Exit(1)
	}
	var man manifest
	if err := json.Unmarshal(raw, &man); err != nil {
		fmt.Fprintf(os.Stderr, "parse manifest: %v\n", err)
		os.Exit(1)
	}

	report := replay.Report{Scenarios: make([]replay.ScenarioOut, 0, len(man.Scenarios))}
	for _, id := range man.Scenarios {
		cfgPath := dataDir + "/" + id + ".json"
		capPath := dataDir + "/" + id + "/docker_network_connectivity_debugger_capture.cnx"
		sc, err := replay.LoadScenario(cfgPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "load %s: %v\n", cfgPath, err)
			os.Exit(1)
		}
		events, capStats, err := capture.Decode(capPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "decode %s: %v\n", capPath, err)
			os.Exit(1)
		}
		sc.Events = events
		capOut := replay.CaptureOut{
			FormatVersion:   capStats.FormatVersion,
			RecordsTotal:    capStats.RecordsTotal,
			RecordsValid:    capStats.RecordsValid,
			RecordsRejected: capStats.RecordsRejected,
			DupSeqRejects:   capStats.DupSeqRejects,
			TruncatedTail:   capStats.TruncatedTail,
			PayloadBytes:    capStats.PayloadBytes,
		}
		report.Scenarios = append(report.Scenarios, replay.Analyze(sc, capOut))
	}

	if err := os.MkdirAll("/app/build", 0o755); err != nil {
		fmt.Fprintf(os.Stderr, "mkdir: %v\n", err)
		os.Exit(1)
	}
	enc, err := json.Marshal(report)
	if err != nil {
		fmt.Fprintf(os.Stderr, "marshal: %v\n", err)
		os.Exit(1)
	}
	out := append(enc, '\n')
	if err := os.WriteFile(outPath, out, 0o644); err != nil {
		fmt.Fprintf(os.Stderr, "write: %v\n", err)
		os.Exit(1)
	}
}
