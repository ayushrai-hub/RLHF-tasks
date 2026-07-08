package main

import (
	"fmt"
	"os"

	"columnarvalidator/codec/ingest"
	"columnarvalidator/codec/reconcile"
	"columnarvalidator/codec/types"
	"columnarvalidator/writer"
)

const outPath = "/app/output/encoding_integrity_report.json"

func main() {
	segments, err := ingest.LoadAll()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	results := make([]types.SegmentResult, 0, len(segments))
	for _, seg := range segments {
		results = append(results, reconcile.ValidateSegment(seg))
	}

	rpt := reconcile.BuildReport(results)
	if err := writer.Write(outPath, rpt); err != nil {
		fmt.Fprintln(os.Stderr, "write report:", err)
		os.Exit(1)
	}
}
