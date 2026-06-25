package hygiene

import (
	"os"
	"path/filepath"
	"strings"
)

func RemoveBuildScratch(out string) error {
	entries, err := os.ReadDir(out)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	for _, entry := range entries {
		if entry.IsDir() && strings.HasPrefix(entry.Name(), ".ostore-build-") {
			if err := os.RemoveAll(filepath.Join(out, entry.Name())); err != nil {
				return err
			}
		}
	}
	return nil
}

func WriteDirect(out string, files map[string][]byte) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	for name, data := range files {
		if err := os.WriteFile(filepath.Join(out, name), data, 0o644); err != nil {
			return err
		}
	}
	return nil
}
