package paths

import "path/filepath"

func Clean(path string) string {
	if path == "" {
		return path
	}
	return filepath.Clean(path)
}
