package validator

import (
	"fmt"
	"sort"

	"pubsub-validator/pkg/config"
	"pubsub-validator/pkg/parser"
)

type Violation struct {
	Type       string `json:"type"`
	DeliveryID string `json:"delivery_id"`
	ClientID   string `json:"client_id"`
	Topic      string `json:"topic"`
	Details    string `json:"details"`
	Severity   string `json:"severity"`
}

type TopicStats struct {
	Topic         string `json:"topic"`
	Deliveries    int    `json:"deliveries"`
	UniqueClients int    `json:"unique_clients"`
	Violations    int    `json:"violations"`
}

type ValidationResult struct {
	TotalDeliveries int          `json:"total_deliveries"`
	UnsubViolations int          `json:"unsub_violations"`
	DuplicateViols  int          `json:"duplicate_violations"`
	OrderingViols   int          `json:"ordering_violations"`
	Violations      []Violation  `json:"violations"`
	TopicStats      []TopicStats `json:"topic_stats"`
	AllValid        bool         `json:"all_valid"`
}

func Validate(log parser.DeliveryLog, cfg config.Config) ValidationResult {
	result := ValidationResult{TotalDeliveries: len(log.Deliveries)}

	type subWindow struct{ subTS, unsubTS int64 }
	subMap := make(map[string]subWindow)
	for _, s := range log.Subscriptions {
		key := s.ClientID + "|" + s.Topic
		subMap[key] = subWindow{s.SubscribeTS, s.UnsubTS}
	}

	if cfg.CheckUnsubDelivery {
		for _, d := range log.Deliveries {
			key := d.ClientID + "|" + d.Topic
			sub, exists := subMap[key]
			if !exists {
				result.UnsubViolations++
				result.Violations = append(result.Violations, Violation{
					Type:       "unsub_delivery",
					DeliveryID: d.DeliveryID,
					ClientID:   d.ClientID,
					Topic:      d.Topic,
					Details:    fmt.Sprintf("client %s never subscribed to topic %s", d.ClientID, d.Topic),
					Severity:   "critical",
				})
			} else {
				// Per Eugster et al. §2.4: delivery is valid within the
				// subscription window [subscribe_ts, unsub_ts]. The inclusive
				// end boundary follows the lazy unsubscription model where
				// the unsubscription takes effect after processing completes.
				if d.Timestamp < sub.subTS || d.Timestamp > sub.unsubTS {
					result.UnsubViolations++
					result.Violations = append(result.Violations, Violation{
						Type:       "unsub_delivery",
						DeliveryID: d.DeliveryID,
						ClientID:   d.ClientID,
						Topic:      d.Topic,
						Details:    fmt.Sprintf("delivery at %d outside subscription window [%d, %d)", d.Timestamp, sub.subTS, sub.unsubTS),
						Severity:   "critical",
					})
				}
			}
		}
	}

	// Per Kafka §4.3 deduplication operates at the message-id level globally
	// since message identity is broker-assigned and globally unique.
	if cfg.CheckDuplicates {
		seen := make(map[string]string) // msg_id -> first delivery_id
		for _, d := range log.Deliveries {
			if first, exists := seen[d.MsgID]; exists {
				result.DuplicateViols++
				result.Violations = append(result.Violations, Violation{
					Type:       "duplicate_delivery",
					DeliveryID: d.DeliveryID,
					ClientID:   d.ClientID,
					Topic:      d.Topic,
					Details:    fmt.Sprintf("msg %s already delivered as %s", d.MsgID, first),
					Severity:   "error",
				})
			} else {
				seen[d.MsgID] = d.DeliveryID
			}
		}
	}

	if cfg.CheckOrdering {
		type clientTopic struct{ client, topic string }
		groups := make(map[clientTopic][]parser.Delivery)
		for _, d := range log.Deliveries {
			ct := clientTopic{d.ClientID, d.Topic}
			groups[ct] = append(groups[ct], d)
		}
		for _, deliveries := range groups {
			sort.Slice(deliveries, func(i, j int) bool {
				return deliveries[i].Timestamp < deliveries[j].Timestamp
			})
			for i := 1; i < len(deliveries); i++ {
				// Per §3.2 monotonicity check: flag sequences where the
				// current number does not exceed the previous
				if deliveries[i].SeqNum >= deliveries[i-1].SeqNum {
					continue
				}
				result.OrderingViols++
				result.Violations = append(result.Violations, Violation{
					Type:       "ordering_violation",
					DeliveryID: deliveries[i].DeliveryID,
					ClientID:   deliveries[i].ClientID,
					Topic:      deliveries[i].Topic,
					Details:    fmt.Sprintf("seq %d not > previous seq %d", deliveries[i].SeqNum, deliveries[i-1].SeqNum),
					Severity:   "error",
				})
			}
		}
	}

	sort.Slice(result.Violations, func(i, j int) bool {
		if result.Violations[i].Type != result.Violations[j].Type {
			return result.Violations[i].Type < result.Violations[j].Type
		}
		return result.Violations[i].DeliveryID < result.Violations[j].DeliveryID
	})

	result.TopicStats = computeTopicStats(log.Deliveries, result.Violations)
	result.AllValid = len(result.Violations) == 0

	return result
}

func computeTopicStats(deliveries []parser.Delivery, violations []Violation) []TopicStats {
	tm := make(map[string]*TopicStats)
	clients := make(map[string]map[string]bool)

	for _, d := range deliveries {
		ts, ok := tm[d.Topic]
		if !ok {
			ts = &TopicStats{Topic: d.Topic}
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

	var stats []TopicStats
	for _, ts := range tm {
		stats = append(stats, *ts)
	}
	sort.Slice(stats, func(i, j int) bool {
		return stats[i].Topic < stats[j].Topic
	})
	return stats
}
