package hygiene

import (
	"os"
	"path/filepath"
)

func CommitFiles(out string, files map[string][]byte) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	tmp, err := os.MkdirTemp(out, ".ostore-build-")
	if err != nil {
		return err
	}
	committed := false
	defer func() {
		if !committed {
			_ = os.RemoveAll(tmp)
		}
	}()
	for name, data := range files {
		if err := os.WriteFile(filepath.Join(tmp, name), data, 0o644); err != nil {
			return err
		}
	}
	for name := range files {
		if err := os.Rename(filepath.Join(tmp, name), filepath.Join(out, name)); err != nil {
			return err
		}
	}
	committed = true
	return os.RemoveAll(tmp)
}
