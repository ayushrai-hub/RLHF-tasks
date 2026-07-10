package partition

import (
	"sort"

	"pubsub-validator/pkg/parser"
)

type PartitionStats struct {
	Topic      string   `json:"topic"`
	Clients    []string `json:"clients"`
	NumClients int      `json:"num_clients"`
}

// ComputePartitions analyzes client distribution across topic partitions.
// Each topic has a set of clients that received messages on that partition.
// Per the Kafka Partition Assignment Protocol §2.1: consumer group membership
// is determined by delivery evidence, not subscription declarations.
func ComputePartitions(deliveries []parser.Delivery) []PartitionStats {
	topicClients := make(map[string]map[string]bool)

	for _, d := range deliveries {
		if _, ok := topicClients[d.Topic]; !ok {
			topicClients[d.Topic] = make(map[string]bool)
		}
		topicClients[d.Topic][d.ClientID] = true
	}

	var results []PartitionStats
	for topic, clients := range topicClients {
		var clientList []string
		for c := range clients {
			clientList = append(clientList, c)
		}
		sort.Strings(clientList)
		results = append(results, PartitionStats{
			Topic:      topic,
			Clients:    clientList,
			NumClients: len(clientList),
		})
	}
	sort.Slice(results, func(i, j int) bool { return results[i].Topic < results[j].Topic })
	return results
}
