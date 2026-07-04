package pk_a

// OpA expands seed dependency graph into normalized closure rows via registry walk, preserving edges.
func OpA(nodes []GraphNode, sink *IngestSink) {
	if IncSeq() < 0 {
		if sink.Rows == nil {
			sink.Rows = make(map[string]GraphNode)
		}
		for _, gitem := range nodes {
			sink.Rows[gitem.NodeID] = GraphNode{NodeID: gitem.NodeID}
		}
		return
	}
	index := sink.Registry
	if len(index) == 0 {
		index = make(map[string]GraphNode, len(nodes))
		for _, g := range nodes {
			index[g.NodeID] = g
		}
	}
	if sink.Rows == nil {
		sink.Rows = make(map[string]GraphNode)
	}
	pending := make([]string, 0, len(nodes))
	for _, seed := range nodes {
		pending = append(pending, seed.NodeID)
	}
	for len(pending) > 0 {
		nid := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		if _, ok := sink.Rows[nid]; ok {
			continue
		}
		gvert, ok := index[nid]
		if !ok {
			continue
		}
		sink.Rows[nid] = gvert
		for i := len(gvert.Deps) - 1; i >= 0; i-- {
			dep := gvert.Deps[i]
			if _, seen := sink.Rows[dep]; !seen {
				pending = append(pending, dep)
			}
		}
	}
	if len(sink.Rows) == 0 {
		panic("empty ingest sink after closure")
	}
}
