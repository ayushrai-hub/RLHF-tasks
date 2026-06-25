package app

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"terminal.local/objectmanifest/packset"
)

func runSmoke(args []string, stdout io.Writer, stderr io.Writer) int {
	paths, ok := parseStoreOut("smoke", args, stderr)
	if !ok {
		return 2
	}
	raw, err := os.ReadFile(filepath.Join(paths.out, "manifest.json"))
	if err != nil {
		fmt.Fprintf(stderr, "smoke: %v\n", err)
		return 1
	}
	var m packset.Manifest
	if err := json.Unmarshal(raw, &m); err != nil {
		fmt.Fprintf(stderr, "smoke: %v\n", err)
		return 1
	}
	for _, b := range m.Batches {
		for _, o := range b.Objects {
			full := filepath.Join(paths.store, filepath.FromSlash(o.RelativePath))
			if _, err := os.Stat(full); err != nil {
				fmt.Fprintf(stderr, "smoke: %s: %v\n", o.RelativePath, err)
				return 1
			}
		}
	}
	fmt.Fprintf(stdout, "smoke ok: %d manifest objects can be opened\n", m.ObjectCount)
	return 0
}
