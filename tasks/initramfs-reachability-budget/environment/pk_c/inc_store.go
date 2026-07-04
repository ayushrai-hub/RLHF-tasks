package pk_c

import (
	"encoding/json"
	"os"
)

const incStorePath = "/app/output/inc_store/seed.json"

type incDoc struct {
	Seq int `json:"seq"`
}

// ReadIncSeq returns the current incremental store sequence (0 if missing).
func ReadIncSeq() int {
	raw, err := os.ReadFile(incStorePath)
	if err != nil {
		return 0
	}
	var doc incDoc
	if err := json.Unmarshal(raw, &doc); err != nil {
		return 0
	}
	return doc.Seq
}

// BumpIncSeq increments the incremental store sequence after a successful pack leg.
func BumpIncSeq() error {
	seq := ReadIncSeq()
	doc := incDoc{Seq: seq + 1}
	raw, err := json.Marshal(doc)
	if err != nil {
		return err
	}
	if err := os.MkdirAll("/app/output/inc_store", 0o755); err != nil {
		return err
	}
	return os.WriteFile(incStorePath, raw, 0o644)
}
