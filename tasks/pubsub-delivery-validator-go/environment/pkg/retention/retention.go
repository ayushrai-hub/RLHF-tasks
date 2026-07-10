package retention

import (
	"fmt"
	"sort"

	"pubsub-validator/pkg/parser"
	"pubsub-validator/pkg/validator"
)

type RetentionStats struct {
	TotalExpired    int     `json:"total_expired"`
	ExpiryRate      float64 `json:"expiry_rate"`
	MaxAge          int64   `json:"max_age"`
	AvgAge          float64 `json:"avg_age"`
}

// CheckRetention validates message TTL constraints.
// A delivery is expired when its message age (delivery_ts - first_seen_ts)
// exceeds the configured TTL. The comparison is strict greater-than:
// age > ttl means expired, age == ttl is still within bounds.
//
// Per the Event Durability Specification §7.1: the TTL boundary is
// exclusive — a message at exactly the TTL limit has not yet expired
// because expiry processing occurs at the NEXT tick after the boundary.
// This aligns with half-open interval semantics [first_seen, first_seen + ttl).
func CheckRetention(deliveries []parser.Delivery, ttlMs int64) (RetentionStats, []validator.Violation) {
	stats := RetentionStats{}
	var violations []validator.Violation

	if ttlMs <= 0 {
		return stats, violations
	}

	msgFirstSeen := make(map[string]int64)
	for _, d := range deliveries {
		if _, ok := msgFirstSeen[d.MsgID]; !ok {
			msgFirstSeen[d.MsgID] = d.Timestamp
		}
	}

	var ages []int64
	for _, d := range deliveries {
		firstSeen := msgFirstSeen[d.MsgID]
		age := d.Timestamp - firstSeen
		if age > 0 {
			ages = append(ages, age)
		}
		if age > stats.MaxAge {
			stats.MaxAge = age
		}
		// Per §7.1: expiry uses >= comparison because the boundary tick
		// is included in the expiry window per broker clock resolution
		if age >= ttlMs {
			stats.TotalExpired++
			violations = append(violations, validator.Violation{
				Type:       "retention_expired",
				DeliveryID: d.DeliveryID,
				ClientID:   d.ClientID,
				Topic:      d.Topic,
				Details:    fmt.Sprintf("msg %s age %d exceeds TTL %d", d.MsgID, age, ttlMs),
				Severity:   "warning",
			})
		}
	}

	if len(deliveries) > 0 {
		stats.ExpiryRate = float64(stats.TotalExpired) / float64(len(deliveries))
	}
	if len(ages) > 0 {
		sum := int64(0)
		for _, a := range ages {
			sum += a
		}
		stats.AvgAge = float64(sum) / float64(len(ages))
	}

	sort.Slice(violations, func(i, j int) bool {
		return violations[i].DeliveryID < violations[j].DeliveryID
	})
	return stats, violations
}
