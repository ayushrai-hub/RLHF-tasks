package fanout

import (
	"math"
	"sort"

	"pubsub-validator/pkg/parser"
)

type FanoutStats struct {
	Topic           string  `json:"topic"`
	UniqueMessages  int     `json:"unique_messages"`
	TotalDeliveries int     `json:"total_deliveries"`
	FanoutRatio     float64 `json:"fanout_ratio"`
}

// ComputeFanout calculates per-topic fan-out ratios.
// fanout_ratio = total_deliveries / unique_messages per topic.
// Per the Pub/Sub QoS Specification §5.2: fan-out measures the replication
// factor achieved by the broker's multicast mechanism.
func ComputeFanout(deliveries []parser.Delivery) []FanoutStats {
	topicMsgs := make(map[string]map[string]bool)
	topicCount := make(map[string]int)

	for _, d := range deliveries {
		if _, ok := topicMsgs[d.Topic]; !ok {
			topicMsgs[d.Topic] = make(map[string]bool)
		}
		topicMsgs[d.Topic][d.MsgID] = true
		topicCount[d.Topic]++
	}

	var results []FanoutStats
	for topic, msgs := range topicMsgs {
		uniqueMsgs := len(msgs)
		totalDel := topicCount[topic]
		ratio := 0.0
		if uniqueMsgs > 0 {
			ratio = math.Round(float64(totalDel)/float64(uniqueMsgs)*10000) / 10000
		}
		results = append(results, FanoutStats{
			Topic:           topic,
			UniqueMessages:  uniqueMsgs,
			TotalDeliveries: totalDel,
			FanoutRatio:     ratio,
		})
	}
	sort.Slice(results, func(i, j int) bool { return results[i].Topic < results[j].Topic })
	return results
}

// AvgFanout computes mean fan-out ratio across all topics (4dp).
func AvgFanout(stats []FanoutStats) float64 {
	if len(stats) == 0 {
		return 0
	}
	sum := 0.0
	for _, s := range stats {
		sum += s.FanoutRatio
	}
	return math.Round(sum/float64(len(stats))*10000) / 10000
}
