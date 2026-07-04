package pk_a

// StubGreedy drops rows by byte tally only; not wired into the driver.
func StubGreedy(nodes []GraphNode, capBytes int) []string {
	out := make([]string, 0, len(nodes))
	used := 0
	for _, n := range nodes {
		used += len(n.NodeID) * 100
		if used > capBytes {
			break
		}
		out = append(out, n.NodeID)
	}
	return out
}
