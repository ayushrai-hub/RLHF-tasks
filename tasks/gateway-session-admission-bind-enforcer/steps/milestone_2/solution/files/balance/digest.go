package balance

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sort"
)

func BuildStateDigest(
	buckets map[string]int,
	configGen int,
	routeCounter int,
	scopeGen int,
	seq int,
	pendingCount int,
) string {
	ids := make([]string, 0, len(buckets))
	for id := range buckets {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	payload := struct {
		Buckets       map[string]int `json:"buckets"`
		ConfigGen     int            `json:"config_gen"`
		RouteCounter  int            `json:"route_counter"`
		ScopeGen      int            `json:"scope_gen"`
		Seq           int            `json:"seq"`
		PendingReload int            `json:"pending_reload_count"`
	}{
		Buckets:       make(map[string]int, len(ids)),
		ConfigGen:     configGen,
		RouteCounter:  routeCounter,
		ScopeGen:      scopeGen,
		Seq:           seq,
		PendingReload: pendingCount,
	}
	for _, id := range ids {
		payload.Buckets[id] = buckets[id]
	}
	raw, _ := json.Marshal(payload)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}
