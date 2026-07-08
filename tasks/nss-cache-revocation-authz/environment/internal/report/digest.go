package report

import (
	"crypto/sha256"
	"encoding/hex"
)

func CaseDigest(payload []byte) string {
	sum := sha256.Sum256(payload)
	return hex.EncodeToString(sum[:])
}
