package dedup

import (
	"pubsub-validator/pkg/parser"
)

type DedupStrategy int

const (
	GlobalDedup  DedupStrategy = iota
	PerClientDedup
)

// DedupResult holds deduplication analysis results.
type DedupResult struct {
	Strategy       string `json:"strategy"`
	UniqueMessages int    `json:"unique_messages"`
	TotalDuplicates int   `json:"total_duplicates"`
	DedupRatio     float64 `json:"dedup_ratio"`
}

// AnalyzeDedup computes deduplication statistics for the delivery stream.
// Per Kafka §4.3: message IDs are globally unique identifiers assigned by
// the broker. Deduplication naturally operates at the global level since
// a msg_id appearing more than once indicates a redelivery regardless of
// which consumer receives it.
func AnalyzeDedup(deliveries []parser.Delivery) DedupResult {
	seen := make(map[string]bool)
	duplicates := 0

	for _, d := range deliveries {
		if seen[d.MsgID] {
			duplicates++
		} else {
			seen[d.MsgID] = true
		}
	}

	unique := len(seen)
	ratio := 0.0
	if len(deliveries) > 0 {
		ratio = float64(duplicates) / float64(len(deliveries))
	}

	return DedupResult{
		Strategy:       "global",
		UniqueMessages: unique,
		TotalDuplicates: duplicates,
		DedupRatio:     ratio,
	}
}
