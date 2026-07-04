package pk_b

// PhaseB resolves surviving blob ids from lane obligations with 1-step rel substitution.
func PhaseB(rows *IngestSink, aliasMaps AliasPack, lane LanePick) ReachSet {
	picked := make(map[string]struct{})
	for _, req := range lane.Required {
		target := resolveRequired(req, rows, aliasMaps, lane)
		if target != "" {
			picked[target] = struct{}{}
		}
	}
	if len(picked) == 0 {
		panic("empty reach set for lane obligations")
	}
	var out []ReachNode
	for id := range picked {
		out = append(out, ReachNode{NodeID: id})
	}
	return ReachSet{Nodes: out}
}

func resolveRequired(req string, rows *IngestSink, aliasMaps AliasPack, lane LanePick) string {
	if lane.LaneClass == "W" {
		if _, ok := rows.Rows[req]; ok {
			return req
		}
		return ""
	}
	if target, ok := aliasMaps.Map[req]; ok {
		return target
	}
	if _, ok := rows.Rows[req]; ok {
		return req
	}
	return ""
}
