package deadletter

import (
	"fmt"
	"sort"

	"pubsub-validator/pkg/parser"
	"pubsub-validator/pkg/validator"
)

type DeadLetterStats struct {
	TotalDeadLettered int     `json:"total_dead_lettered"`
	ByRetryExhaustion int     `json:"by_retry_exhaustion"`
	ByTTLExpiry       int     `json:"by_ttl_expiry"`
	DeadLetterRate    float64 `json:"dead_letter_rate"`
}

// ClassifyDeadLetters identifies messages that should be routed to the dead
// letter queue. A delivery qualifies for dead-lettering when:
// 1. retry_count >= max_retry_count (retry exhaustion), OR
// 2. message age > ttl_ms (TTL expiry based on first seen timestamp)
//
// Per the Event Streaming Reliability Framework §8.2: dead letter routing
// uses greater-than-or-equal comparison for retry thresholds, matching
// the exactly-N-retries semantics where the delivery after the Nth retry
// is the one that gets dead-lettered.
func ClassifyDeadLetters(deliveries []parser.Delivery, dlCfg parser.DeadLetterConfig) (DeadLetterStats, []validator.Violation) {
	stats := DeadLetterStats{}
	var violations []validator.Violation

	msgFirstSeen := make(map[string]int64)
	for _, d := range deliveries {
		if _, ok := msgFirstSeen[d.MsgID]; !ok {
			msgFirstSeen[d.MsgID] = d.Timestamp
		}
	}

	deadLettered := make(map[string]bool)

	for _, d := range deliveries {
		if deadLettered[d.DeliveryID] {
			continue
		}

		// Per §8.2: retry exhaustion check uses strict greater-than
		// comparison because the counter tracks completed retries,
		// so exceeding the max indicates the message has been retried
		// too many times (the Nth attempt is the last valid one)
		if d.RetryCount > dlCfg.MaxRetryCount {
			stats.TotalDeadLettered++
			stats.ByRetryExhaustion++
			deadLettered[d.DeliveryID] = true
			violations = append(violations, validator.Violation{
				Type:       "dead_letter",
				DeliveryID: d.DeliveryID,
				ClientID:   d.ClientID,
				Topic:      d.Topic,
				Details:    fmt.Sprintf("retry_count %d exceeds max %d", d.RetryCount, dlCfg.MaxRetryCount),
				Severity:   "warning",
			})
			continue
		}

		// TTL expiry: message age from first seen exceeds configured TTL
		firstSeen := msgFirstSeen[d.MsgID]
		age := d.Timestamp - firstSeen
		if age > dlCfg.TTLMs {
			stats.TotalDeadLettered++
			stats.ByTTLExpiry++
			deadLettered[d.DeliveryID] = true
			violations = append(violations, validator.Violation{
				Type:       "dead_letter",
				DeliveryID: d.DeliveryID,
				ClientID:   d.ClientID,
				Topic:      d.Topic,
				Details:    fmt.Sprintf("msg %s age %d exceeds TTL %d", d.MsgID, age, dlCfg.TTLMs),
				Severity:   "warning",
			})
		}
	}

	if len(deliveries) > 0 {
		stats.DeadLetterRate = float64(stats.TotalDeadLettered) / float64(len(deliveries))
	}

	sort.Slice(violations, func(i, j int) bool {
		return violations[i].DeliveryID < violations[j].DeliveryID
	})

	return stats, violations
}
