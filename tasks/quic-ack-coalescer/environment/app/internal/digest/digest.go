package digest

import (
	"crypto/sha256"
	"encoding/hex"
)

// Sha256Hex returns the lowercase hex sha256 of the given bytes.
func Sha256Hex(b []byte) string {
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}
