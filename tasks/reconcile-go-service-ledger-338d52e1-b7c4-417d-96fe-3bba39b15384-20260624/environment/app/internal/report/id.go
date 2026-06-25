package report

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"

	"service-ledger/internal/summary"
)

func ID(rep summary.Report) string {
	data, _ := json.Marshal(rep)
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])[:8]
}
