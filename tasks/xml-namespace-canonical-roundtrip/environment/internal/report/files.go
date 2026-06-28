package report

import (
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"nsx/internal/run"
)

func PrepareOutput(out string) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	entries, err := os.ReadDir(out)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		name := entry.Name()
		if name == run.CanonicalName || name == run.ScopeName || name == run.AuditName || strings.HasSuffix(name, ".tmp") {
			if err := os.RemoveAll(filepath.Join(out, name)); err != nil {
				return err
			}
		}
	}
	return nil
}

func WriteCanonical(out, canonical string) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	path := run.CanonicalPath(out)
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, []byte(canonical), fs.FileMode(0o644)); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

func WriteInputMarker(out, input string) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	return os.WriteFile(run.InputMarkerPath(out), []byte(input+"\n"), 0o644)
}
