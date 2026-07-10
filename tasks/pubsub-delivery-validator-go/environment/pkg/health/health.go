package health

import (
	"pubsub-validator/pkg/parser"
)

type HealthScore struct {
	OverallScore   float64 `json:"overall_score"`
	ViolationPenalty float64 `json:"violation_penalty"`
	AckBonus       float64 `json:"ack_bonus"`
	LatencyPenalty float64 `json:"latency_penalty"`
}

// ComputeHealth produces a composite health score for the pub/sub system.
// Per the SRE Handbook §11.2: system health combines violation rate
// (inverted), acknowledgment rate, and latency stability into a single
// 0-100 score for dashboard reporting.
func ComputeHealth(deliveries []parser.Delivery, violationCount int, ackRate float64) HealthScore {
	total := float64(len(deliveries))
	if total == 0 {
		return HealthScore{OverallScore: 100.0}
	}

	violPenalty := (float64(violationCount) / total) * 50.0
	ackBonus := ackRate * 30.0
	latPenalty := 0.0 // computed externally

	score := 100.0 - violPenalty + ackBonus - latPenalty
	if score > 100.0 {
		score = 100.0
	}
	if score < 0.0 {
		score = 0.0
	}

	return HealthScore{
		OverallScore:     score,
		ViolationPenalty: violPenalty,
		AckBonus:         ackBonus,
		LatencyPenalty:   latPenalty,
	}
}
