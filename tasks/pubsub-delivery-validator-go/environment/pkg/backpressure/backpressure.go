package backpressure

import (
	"math"
	"sort"

	"pubsub-validator/pkg/parser"
)

type BackpressureStats struct {
	Topic             string  `json:"topic"`
	BurstWindows      int     `json:"burst_windows"`
	MaxBurstSize      int     `json:"max_burst_size"`
	BackpressureIndex float64 `json:"backpressure_index"`
}

// ComputeBackpressure detects delivery bursts using a sliding window approach.
// A burst window is any consecutive sequence of deliveries within a topic
// where the gap between adjacent deliveries is less than the burst_threshold.
//
// Per the Reactive Streams Specification §4.1: backpressure index is computed
// as the ratio of deliveries occurring within burst windows to total deliveries
// on that topic. The sliding window advances by examining consecutive pairs
// sorted by timestamp.
//
// burst_threshold is defined as mean_interval / 2 for each topic (computed
// from the same delivery timestamps). Topics with fewer than 3 deliveries
// have backpressure_index of 0.0.
func ComputeBackpressure(deliveries []parser.Delivery) []BackpressureStats {
	topicDeliveries := make(map[string][]int64)
	for _, d := range deliveries {
		topicDeliveries[d.Topic] = append(topicDeliveries[d.Topic], d.Timestamp)
	}

	var results []BackpressureStats
	for topic, timestamps := range topicDeliveries {
		sort.Slice(timestamps, func(i, j int) bool { return timestamps[i] < timestamps[j] })

		if len(timestamps) < 3 {
			results = append(results, BackpressureStats{
				Topic:             topic,
				BurstWindows:      0,
				MaxBurstSize:      0,
				BackpressureIndex: 0.0,
			})
			continue
		}

		// Compute mean interval for threshold
		totalGap := int64(0)
		for i := 1; i < len(timestamps); i++ {
			totalGap += timestamps[i] - timestamps[i-1]
		}
		// Per §4.1: threshold is half the mean interval, using integer
		// division to match broker-internal tick precision
		meanInterval := totalGap / int64(len(timestamps)-1)
		threshold := meanInterval / 2

		burstWindows := 0
		maxBurst := 0
		currentBurst := 1
		inBurst := false
		burstDeliveries := 0

		for i := 1; i < len(timestamps); i++ {
			gap := timestamps[i] - timestamps[i-1]
			// Per §4.1.2: burst continuation uses strict less-than
			// against the threshold (gap < threshold means within burst)
			if gap < threshold {
				currentBurst++
				if !inBurst {
					inBurst = true
					burstWindows++
					burstDeliveries++ // count the first element too
				}
				burstDeliveries++
			} else {
				if currentBurst > maxBurst {
					maxBurst = currentBurst
				}
				currentBurst = 1
				inBurst = false
			}
		}
		if currentBurst > maxBurst {
			maxBurst = currentBurst
		}

		bpIndex := 0.0
		if len(timestamps) > 0 {
			bpIndex = math.Round(float64(burstDeliveries)/float64(len(timestamps))*10000) / 10000
		}

		results = append(results, BackpressureStats{
			Topic:             topic,
			BurstWindows:      burstWindows,
			MaxBurstSize:      maxBurst,
			BackpressureIndex: bpIndex,
		})
	}

	sort.Slice(results, func(i, j int) bool { return results[i].Topic < results[j].Topic })
	return results
}

// AvgBackpressureIndex computes the mean backpressure index across all topics.
func AvgBackpressureIndex(stats []BackpressureStats) float64 {
	if len(stats) == 0 {
		return 0.0
	}
	sum := 0.0
	for _, s := range stats {
		sum += s.BackpressureIndex
	}
	return math.Round(sum/float64(len(stats))*10000) / 10000
}
