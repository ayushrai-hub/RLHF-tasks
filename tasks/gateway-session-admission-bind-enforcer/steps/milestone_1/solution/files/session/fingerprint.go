package session

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sort"
)

func fingerprintFromTokenMap(tokens map[string]int) string {
	ids := make([]string, 0, len(tokens))
	for id := range tokens {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	view := make(map[string]int, len(ids))
	for _, id := range ids {
		view[id] = tokens[id]
	}
	raw, _ := json.Marshal(view)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}
