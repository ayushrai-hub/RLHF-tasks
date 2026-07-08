package seal

import (
	"os"
	"path/filepath"
	"strings"
)

const tipName = ".mregtip"

func ContinueScan(scanDir string) bool {
	_, err := os.Stat(filepath.Join(scanDir, ".mreg_continue"))
	return err == nil
}

func SeedPrior(scanDir, outDir string) string {
	if !ContinueScan(scanDir) {
		return ""
	}
	raw, err := os.ReadFile(filepath.Join(outDir, tipName))
	if err != nil {
		return ""
	}
	s := strings.TrimSpace(string(raw))
	if len(s) != 64 {
		return ""
	}
	return s
}

func PersistTip(outDir, rootHex string) error {
	if rootHex == "" {
		return nil
	}
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(outDir, tipName), []byte(rootHex), 0o644)
}
