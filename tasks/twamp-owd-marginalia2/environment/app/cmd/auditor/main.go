package main

import (
	"flag"
	"fmt"
	"os"

	"twampowd/internal/aggregate"
	"twampowd/internal/allocate"
	"twampowd/internal/config"
	"twampowd/internal/digest"
	"twampowd/internal/emit"
	"twampowd/internal/loader"
	"twampowd/internal/types"
	"twampowd/internal/verdict"
	"twampowd/internal/window"
)

func main() {
	dataDir := flag.String("data", "/app/data", "path to data directory")
	outPath := flag.String("out", "/app/output/report.json", "path to output JSON")
	flag.Parse()

	if v := os.Getenv("TWAMP_AUDIT_DATA_DIR"); v != "" {
		*dataDir = v
	}
	if v := os.Getenv("TWAMP_AUDIT_OUT_PATH"); v != "" {
		*outPath = v
	}

	cfg, refls, probes, markers, err := loader.Load(*dataDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "load:", err)
		os.Exit(1)
	}

	probes = config.Canonicalize(probes)
	probes = window.Validity(probes, cfg)
	probes = aggregate.Dedup(probes)

	verdict.Classify(probes, cfg)
	probes = aggregate.Cascade(probes, cfg)
	verdict.Jitter(probes, cfg)

	probes, suppressedByRefl := aggregate.ApplyMarkers(probes, markers, cfg)
	probes = aggregate.SyntheticOffline(probes, refls)

	cycles := aggregate.CycleRows(probes, cfg)
	reflRows := aggregate.ReflectorRows(probes, refls, suppressedByRefl)
	shares := allocate.JitterShares(probes, refls)
	for i := range reflRows {
		reflRows[i].JitterSharePermille = shares[reflRows[i].ReflectorID]
	}

	probeRows := aggregate.ProbeRows(probes)

	rep := types.Report{
		SchemaVersion: "1.0",
		Summary: types.Summary{
			TotalProbes:         len(probeRows),
			AlignedGood:         aggregate.CountVerdict(probes, "WITHIN_BOUNDS"),
			Cycles:              len(cycles),
			ByVerdict:           aggregate.ByVerdict(probes),
			JitterSharePermille: shares,
		},
		Reflectors: reflRows,
		Cycles:     cycles,
		Probes:     probeRows,
	}
	rep.ReportDigest = digest.Report(rep)
	rep.Summary.ReportDigest = rep.ReportDigest

	if err := emit.Write(*outPath, rep); err != nil {
		fmt.Fprintln(os.Stderr, "emit:", err)
		os.Exit(1)
	}
}
