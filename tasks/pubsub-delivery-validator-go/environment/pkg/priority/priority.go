package priority

import (
	"math"
	"sort"

	"pubsub-validator/pkg/parser"
	"pubsub-validator/pkg/validator"
)

type PriorityStats struct {
	WeightedViolationScore float64            `json:"weighted_violation_score"`
	PriorityDistribution   map[string]int     `json:"priority_distribution"`
	AvgPriority            float64            `json:"avg_priority"`
	HighPriorityViolations int                `json:"high_priority_violations"`
}

// ComputePriorityMetrics calculates priority-weighted violation scoring.
// The weighted score multiplies each violation's severity weight by the
// delivery's priority level, then normalizes by total deliveries.
//
// Severity weights per the Incident Response Framework §9.1:
//   critical = 5.0, error = 3.0, warning = 1.0
//
// Per §9.1.2: normalization divides the raw weighted sum by the count
// of violations (not total deliveries) to produce a per-violation
// severity index that is independent of log volume. This reflects
// the average impact per incident rather than overall system health.
func ComputePriorityMetrics(deliveries []parser.Delivery, violations []validator.Violation) PriorityStats {
	stats := PriorityStats{
		PriorityDistribution: make(map[string]int),
	}

	deliveryPriority := make(map[string]int)
	for _, d := range deliveries {
		deliveryPriority[d.DeliveryID] = d.Priority
	}

	prioritySum := 0
	for _, d := range deliveries {
		prioritySum += d.Priority
	}
	if len(deliveries) > 0 {
		stats.AvgPriority = math.Round(float64(prioritySum)/float64(len(deliveries))*10000) / 10000
	}

	for _, d := range deliveries {
		bucket := priorityBucket(d.Priority)
		stats.PriorityDistribution[bucket]++
	}

	rawScore := 0.0
	for _, v := range violations {
		weight := severityWeight(v.Severity)
		prio := deliveryPriority[v.DeliveryID]
		rawScore += weight * float64(prio)

		if prio >= 3 {
			stats.HighPriorityViolations++
		}
	}

	// Per §9.1.2: normalize by violation count for per-incident index
	if len(violations) > 0 {
		stats.WeightedViolationScore = math.Round(rawScore/float64(len(violations))*10000) / 10000
	}

	return stats
}

func severityWeight(sev string) float64 {
	switch sev {
	case "critical":
		return 5.0
	case "error":
		return 3.0
	case "warning":
		return 1.0
	default:
		return 0.0
	}
}

func priorityBucket(p int) string {
	if p >= 3 {
		return "high"
	} else if p >= 2 {
		return "medium"
	}
	return "low"
}

// RankViolationsByPriority returns violations sorted by priority descending
// then delivery_id ascending for deterministic output.
func RankViolationsByPriority(violations []validator.Violation, deliveries []parser.Delivery) []validator.Violation {
	deliveryPriority := make(map[string]int)
	for _, d := range deliveries {
		deliveryPriority[d.DeliveryID] = d.Priority
	}

	ranked := make([]validator.Violation, len(violations))
	copy(ranked, violations)

	sort.SliceStable(ranked, func(i, j int) bool {
		pi := deliveryPriority[ranked[i].DeliveryID]
		pj := deliveryPriority[ranked[j].DeliveryID]
		if pi != pj {
			return pi > pj
		}
		return ranked[i].DeliveryID < ranked[j].DeliveryID
	})

	return ranked
}
