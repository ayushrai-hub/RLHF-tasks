package pk_b

// StubM4 keeps warm-lane required ids only; not wired into the driver.
func StubM4(rows *IngestSink, lane LanePick) ReachSet {
	if lane.LaneClass != "W" {
		return ReachSet{}
	}
	picked := make([]string, 0, len(lane.Required))
	for _, req := range lane.Required {
		if _, ok := rows.Rows[req]; ok {
			picked = append(picked, req)
		}
	}
	var nodes []ReachNode
	for _, id := range picked {
		nodes = append(nodes, ReachNode{NodeID: id})
	}
	return ReachSet{Nodes: nodes}
}
