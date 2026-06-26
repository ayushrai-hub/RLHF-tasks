package membership

import "logrecover/pkg/api"

// Eligible reports whether a node may contribute frames at epoch.
func Eligible(node api.NodeState, epoch int) bool {
	if !node.Partitioned {
		return true
	}
	return node.PartitionEpoch < epoch
}
