package app

import (
	"fmt"
	"io"

	"terminal.local/objectmanifest/auditx"
	"terminal.local/objectmanifest/internal/hygiene"
	"terminal.local/objectmanifest/internal/report"
	"terminal.local/objectmanifest/internal/store"
	"terminal.local/objectmanifest/packset"
)

func runRebuild(args []string, stdout io.Writer, stderr io.Writer) int {
	paths, ok := parseStoreOut("rebuild", args, stderr)
	if !ok {
		return 2
	}

	layout := store.NewLayout(paths.store)
	built, err := packset.Build(layout)
	if err != nil {
		fmt.Fprintf(stderr, "rebuild: %v\n", err)
		return 1
	}

	manifestBytes, err := packset.Render(built.Manifest)
	if err != nil {
		fmt.Fprintf(stderr, "render manifest: %v\n", err)
		return 1
	}
	reportBytes := report.RenderTSV(built.ReportRows)
	provenanceBytes, err := auditx.Render(auditx.RecordFromOutputs(built, manifestBytes, reportBytes))
	if err != nil {
		fmt.Fprintf(stderr, "render provenance: %v\n", err)
		return 1
	}

	files := map[string][]byte{
		"manifest.json":       manifestBytes,
		"checksum-report.tsv": reportBytes,
		"provenance.json":     provenanceBytes,
	}
	if err := hygiene.WriteDirect(paths.out, files); err != nil {
		fmt.Fprintf(stderr, "write outputs: %v\n", err)
		return 1
	}
	fmt.Fprintf(stdout, "wrote %d batches and %d objects\n", built.Manifest.CommitCount, built.Manifest.ObjectCount)
	return 0
}
