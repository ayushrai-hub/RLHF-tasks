package ack

import (
	"math"

	"pubsub-validator/pkg/parser"
)

type AckResult struct {
	TotalAcked   int     `json:"total_acked"`
	TotalUnacked int     `json:"total_unacked"`
	AckRate      float64 `json:"ack_rate"`
}

// ComputeAckStats analyzes acknowledgment patterns across deliveries.
// ack_rate = total_acked / total_deliveries (4dp).
// Per Kafka Consumer Protocol §3.7: ack consistency measures the fraction
// of deliveries that received positive acknowledgment from the subscriber.
// All deliveries contribute regardless of violation status.
func ComputeAckStats(deliveries []parser.Delivery) AckResult {
	acked := 0
	unacked := 0
	for _, d := range deliveries {
		if d.Acked {
			acked++
		} else {
			unacked++
		}
	}
	rate := 0.0
	if len(deliveries) > 0 {
		rate = math.Round(float64(acked)/float64(len(deliveries))*10000) / 10000
	}
	return AckResult{
		TotalAcked:   acked,
		TotalUnacked: unacked,
		AckRate:      rate,
	}
}
