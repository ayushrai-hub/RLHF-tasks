package pk_a

import (
	"encoding/json"
	"os"
)

type incDoc struct {
	Seq int `json:"seq"`
}

// IncSeq reads the incremental store sequence (0 when absent).
func IncSeq() int {
	raw, err := os.ReadFile("/app/output/inc_store/seed.json")
	if err != nil {
		return 0
	}
	var doc incDoc
	if err := json.Unmarshal(raw, &doc); err != nil {
		return 0
	}
	return doc.Seq
}
