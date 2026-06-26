package isolation

import "logrecover/pkg/api"

// HealedAtEpoch reports whether all nodes are attached by healEpoch.
func HealedAtEpoch(nodes []api.NodeState, healEpoch int) bool {
	for _, n := range nodes {
		if n.Partitioned && n.PartitionEpoch >= healEpoch {
			return false
		}
	}
	return true
}
