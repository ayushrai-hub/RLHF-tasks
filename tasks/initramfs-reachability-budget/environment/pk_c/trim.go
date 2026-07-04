package pk_c

import "lab/pk_b"

// Trim drops heavy blob ids by size tally only; legacy warm-lane helper, not wired.
func Trim(reachable ReachSet, blobs BlobPack, capBytes int) ReachSet {
	used := 0
	var out []pk_b.ReachNode
	for _, node := range reachable.Nodes {
		used += blobs.Sizes[node.NodeID]
		if used > capBytes {
			break
		}
		out = append(out, node)
	}
	return ReachSet{Nodes: out}
}
