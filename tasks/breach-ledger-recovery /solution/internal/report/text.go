package report

import (
	"os"
	"path/filepath"
	"strings"
)

func R3(out string, iocs []string) error {
	return os.WriteFile(filepath.Join(out, "iocs.txt"), []byte(strings.Join(iocs, "\n")+"\n"), 0o644)
}
