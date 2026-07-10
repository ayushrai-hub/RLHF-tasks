package report

import (
	"math"
	"sort"

	"pubsub-validator/pkg/ack"
	"pubsub-validator/pkg/backpressure"
	"pubsub-validator/pkg/config"
	"pubsub-validator/pkg/deadletter"
	"pubsub-validator/pkg/fanout"
	"pubsub-validator/pkg/latency"
	"pubsub-validator/pkg/parser"
	"pubsub-validator/pkg/priority"
	"pubsub-validator/pkg/retention"
	"pubsub-validator/pkg/throttle"
	"pubsub-validator/pkg/validator"
)

type Report struct {
	Summary        Summary                       `json:"summary"`
	Violations     []validator.Violation         `json:"violations"`
	TopicStats     []validator.TopicStats        `json:"topic_stats"`
	Metrics        Metrics                       `json:"metrics"`
	Latency        []latency.LatencyStats        `json:"latency"`
	Fanout         []fanout.FanoutStats          `json:"fanout"`
	AckStats       ack.AckResult                 `json:"ack_stats"`
	DeadLetter     deadletter.DeadLetterStats    `json:"dead_letter"`
	Priority       priority.PriorityStats        `json:"priority"`
	Backpressure   []backpressure.BackpressureStats `json:"backpressure"`
	Throttle       []throttle.ThrottleStats      `json:"throttle"`
	Retention      retention.RetentionStats      `json:"retention"`
}

type Summary struct {
	TotalDeliveries int  `json:"total_deliveries"`
	UnsubViolations int  `json:"unsub_violations"`
	DuplicateViols  int  `json:"duplicate_violations"`
	OrderingViols   int  `json:"ordering_violations"`
	DeadLettered    int  `json:"dead_lettered"`
	NumViolations   int  `json:"num_violations"`
	NumTopics       int  `json:"num_topics"`
	AllValid        bool `json:"all_valid"`
}

type Metrics struct {
	UnsubRate           float64 `json:"unsub_rate"`
	DuplicateRate       float64 `json:"duplicate_rate"`
	OrderingRate        float64 `json:"ordering_rate"`
	ViolationRate       float64 `json:"violation_rate"`
	AvgMeanInterval     float64 `json:"avg_mean_interval"`
	AvgFanout           float64 `json:"avg_fanout"`
	AckRate             float64 `json:"ack_rate"`
	DeadLetterRate      float64 `json:"dead_letter_rate"`
	AvgBackpressure     float64 `json:"avg_backpressure"`
	WeightedViolScore   float64 `json:"weighted_violation_score"`
}

func Generate(result validator.ValidationResult, cfg config.Config, log parser.DeliveryLog) Report {
	deliveries := log.Deliveries
	latStats := latency.ComputeLatency(deliveries)
	ackStats := ack.ComputeAckStats(deliveries)
	fanStats := fanout.ComputeFanout(deliveries)
	dlStats, dlViols := deadletter.ClassifyDeadLetters(deliveries, log.DeadLetterConfig)
	retStats, retViols := retention.CheckRetention(deliveries, log.DeadLetterConfig.TTLMs)
	bpStats := backpressure.ComputeBackpressure(deliveries)
	thrStats := throttle.ComputeThrottle(deliveries)

	// Merge all violations: core + deadletter + retention
	allViolations := make([]validator.Violation, 0, len(result.Violations)+len(dlViols)+len(retViols))
	allViolations = append(allViolations, result.Violations...)
	allViolations = append(allViolations, dlViols...)
	allViolations = append(allViolations, retViols...)

	// Sort all violations by type then delivery_id
	sort.Slice(allViolations, func(i, j int) bool {
		if allViolations[i].Type != allViolations[j].Type {
			return allViolations[i].Type < allViolations[j].Type
		}
		return allViolations[i].DeliveryID < allViolations[j].DeliveryID
	})

	// Recompute topic stats including all violation types
	topicStats := computeFullTopicStats(deliveries, allViolations)

	// Compute priority metrics on core violations only (not deadletter/retention)
	prioStats := priority.ComputePriorityMetrics(deliveries, result.Violations)

	r := Report{
		Summary: Summary{
			TotalDeliveries: result.TotalDeliveries,
			UnsubViolations: result.UnsubViolations,
			DuplicateViols:  result.DuplicateViols,
			OrderingViols:   result.OrderingViols,
			DeadLettered:    dlStats.TotalDeadLettered,
			NumViolations:   len(allViolations),
			NumTopics:       len(topicStats),
			AllValid:        len(allViolations) == 0,
		},
		Violations:   allViolations,
		TopicStats:   topicStats,
		Latency:      latStats,
		Fanout:       fanStats,
		AckStats:     ackStats,
		DeadLetter:   dlStats,
		Priority:     prioStats,
		Backpressure: bpStats,
		Throttle:     thrStats,
		Retention:    retStats,
	}

	total := result.TotalDeliveries
	if total > 0 {
		r.Metrics.UnsubRate = roundTo4(float64(result.UnsubViolations) / float64(total))
		r.Metrics.DuplicateRate = roundTo4(float64(result.DuplicateViols) / float64(total))
		r.Metrics.OrderingRate = roundTo4(float64(result.OrderingViols) / float64(total))
		r.Metrics.ViolationRate = roundTo4(float64(len(allViolations)) / float64(total))
		r.Metrics.DeadLetterRate = roundTo4(float64(dlStats.TotalDeadLettered) / float64(total))
	}

	r.Metrics.AvgMeanInterval = latency.AvgMeanInterval(latStats)
	r.Metrics.AvgFanout = fanout.AvgFanout(fanStats)
	r.Metrics.AckRate = ackStats.AckRate
	r.Metrics.AvgBackpressure = backpressure.AvgBackpressureIndex(bpStats)
	r.Metrics.WeightedViolScore = prioStats.WeightedViolationScore

	return r
}

func roundTo4(v float64) float64 {
	return math.Round(v*10000) / 10000
}

func computeFullTopicStats(deliveries []parser.Delivery, violations []validator.Violation) []validator.TopicStats {
	tm := make(map[string]*validator.TopicStats)
	clients := make(map[string]map[string]bool)

	for _, d := range deliveries {
		ts, ok := tm[d.Topic]
		if !ok {
			ts = &validator.TopicStats{Topic: d.Topic}
			tm[d.Topic] = ts
			clients[d.Topic] = make(map[string]bool)
		}
		ts.Deliveries++
		clients[d.Topic][d.ClientID] = true
	}

	for topic, cs := range clients {
		tm[topic].UniqueClients = len(cs)
	}

	for _, v := range violations {
		if ts, ok := tm[v.Topic]; ok {
			ts.Violations++
		}
	}

	var stats []validator.TopicStats
	for _, ts := range tm {
		stats = append(stats, *ts)
	}
	sort.Slice(stats, func(i, j int) bool {
		return stats[i].Topic < stats[j].Topic
	})
	return stats
}
