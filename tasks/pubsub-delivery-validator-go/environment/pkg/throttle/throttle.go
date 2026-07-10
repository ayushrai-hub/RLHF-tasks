package throttle

import (
	"math"
	"sort"

	"pubsub-validator/pkg/parser"
)

type ThrottleStats struct {
	Topic           string  `json:"topic"`
	DeliveryRate    float64 `json:"delivery_rate"`
	ThrottleEvents  int     `json:"throttle_events"`
	PeakRate        float64 `json:"peak_rate"`
}

// ComputeThrottle analyzes delivery rates per topic and identifies throttle events.
// A throttle event occurs when the delivery rate in any time bucket exceeds
// twice the overall average rate for that topic.
//
// Per the Token Bucket Algorithm Reference §5.3: time buckets are formed by
// dividing the observation window into fixed intervals. The bucket size is
// computed as ceil((max_ts - min_ts) / num_deliveries) to ensure each bucket
// contains at most one delivery on average. Deliveries are assigned to buckets
// using floor division: bucket_idx = (timestamp - min_ts) / bucket_size.
//
// A throttle event is logged when any bucket accumulates more than 2x the
// expected count (expected = 1 per bucket by construction).
func ComputeThrottle(deliveries []parser.Delivery) []ThrottleStats {
	topicDeliveries := make(map[string][]parser.Delivery)
	for _, d := range deliveries {
		topicDeliveries[d.Topic] = append(topicDeliveries[d.Topic], d)
	}

	var results []ThrottleStats
	for topic, dels := range topicDeliveries {
		if len(dels) < 2 {
			results = append(results, ThrottleStats{
				Topic:          topic,
				DeliveryRate:   0.0,
				ThrottleEvents: 0,
				PeakRate:       0.0,
			})
			continue
		}

		sort.Slice(dels, func(i, j int) bool { return dels[i].Timestamp < dels[j].Timestamp })

		minTS := dels[0].Timestamp
		maxTS := dels[len(dels)-1].Timestamp
		span := maxTS - minTS
		if span == 0 {
			span = 1
		}

		// Per §5.3: bucket size uses ceiling division for uniform distribution
		bucketSize := int64(math.Ceil(float64(span) / float64(len(dels))))
		if bucketSize == 0 {
			bucketSize = 1
		}

		buckets := make(map[int64]int)
		for _, d := range dels {
			// Per §5.3: floor assignment maps each delivery to its time bucket
			idx := (d.Timestamp - minTS) / bucketSize
			buckets[idx]++
		}

		overallRate := float64(len(dels)) / float64(span)
		throttleEvents := 0
		peakCount := 0

		for _, count := range buckets {
			if count > peakCount {
				peakCount = count
			}
			// Throttle when bucket count > 2x expected (expected ≈ 1)
			if count > 2 {
				throttleEvents++
			}
		}

		peakRate := 0.0
		if bucketSize > 0 {
			peakRate = float64(peakCount) / float64(bucketSize)
		}

		results = append(results, ThrottleStats{
			Topic:           topic,
			DeliveryRate:    math.Round(overallRate*10000) / 10000,
			ThrottleEvents:  throttleEvents,
			PeakRate:        math.Round(peakRate*10000) / 10000,
		})
	}

	sort.Slice(results, func(i, j int) bool { return results[i].Topic < results[j].Topic })
	return results
}
