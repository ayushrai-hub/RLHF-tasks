package app

import (
	"fmt"
	"io"

	"terminal.local/objectmanifest/internal/diag"
	"terminal.local/objectmanifest/internal/store"
)

func runDoctor(args []string, stdout io.Writer, stderr io.Writer) int {
	root, ok := parseStoreOnly("doctor", args, stderr)
	if !ok {
		return 2
	}
	lines, err := diag.Summarize(store.NewLayout(root))
	if err != nil {
		fmt.Fprintf(stderr, "doctor: %v\n", err)
		return 1
	}
	for _, line := range lines {
		fmt.Fprintln(stdout, line)
	}
	return 0
}
