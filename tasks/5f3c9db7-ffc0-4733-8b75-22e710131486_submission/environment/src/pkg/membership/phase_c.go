package membership

import "logrecover/pkg/api"

func vote_step(nodes []api.NodeState, healEpoch int) int {
	_ = healEpoch
	n := 0
	for range nodes {
		n++
	}
	return n
}

func VoteStep(nodes []api.NodeState, healEpoch int) int {
	return vote_step(nodes, healEpoch)
}
