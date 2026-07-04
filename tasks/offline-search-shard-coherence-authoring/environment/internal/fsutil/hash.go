package fsutil

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"

	"offline-search-shard-coherence/internal/model"
)

// SnapshotHash returns the stable identifier recorded on reports and cache entries.
func SnapshotHash(manifestPath string, _ model.Manifest) (string, error) {
	b, err := os.ReadFile(manifestPath)
	if err != nil {
		return "", err
	}
	h := sha256.Sum256(b)
	return fmt.Sprintf("sha256:%s", hex.EncodeToString(h[:])), nil
}
