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
	return strings.TrimSpace(string(raw))
}

func PersistTip(outDir, rootHex string) error {
	return nil
}
