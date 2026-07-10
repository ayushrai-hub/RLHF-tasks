package report

import (
	"os"
	"path/filepath"
)

func R3(out string, iocs []string) error {
	text := ""
	for _, ioc := range iocs {
		text += ioc + "\n"
	}
	return os.WriteFile(filepath.Join(out, "iocs.txt"), []byte(text), 0o644)
}
