package pk_b

import "lab/pk_a"

// PhaseB resolves surviving blob ids from lane obligations with transitive rel substitution and cycle breaking.
func PhaseB(rows *pk_a.IngestSink, aliasMaps AliasPack, lane LanePick, blobSizes map[string]int) ReachSet {
	uniq := make(map[string]struct{})
	var out []ReachNode
	for _, req := range lane.Required {
		target := resolveRequired(req, rows, aliasMaps, lane, blobSizes)
		if target != "" {
			if _, seen := uniq[target]; !seen {
				uniq[target] = struct{}{}
				out = append(out, ReachNode{
					NodeID: target,
					Deps:   resolveDeps(rows.Rows[req].Deps, rows, aliasMaps, lane, blobSizes),
				})
			}
		}
	}
	if len(out) == 0 {
		panic("empty reach set for lane obligations")
	}
	return ReachSet{Nodes: out}
}

func resolveDeps(deps []string, rows *pk_a.IngestSink, aliasMaps AliasPack, lane LanePick, blobSizes map[string]int) []string {
	if len(deps) == 0 {
		return nil
	}
	out := make([]string, 0, len(deps))
	for _, dep := range deps {
		target := resolveRequired(dep, rows, aliasMaps, lane, blobSizes)
		if target != "" {
			out = append(out, target)
		}
	}
	return out
}

func resolveRequired(req string, rows *pk_a.IngestSink, aliasMaps AliasPack, lane LanePick, blobSizes map[string]int) string {
	if lane.LaneClass == "W" {
		if _, ok := rows.Rows[req]; ok {
			return req
		}
		return ""
	}

	seen := make(map[string]struct{})
	current := req
	var cycle []string

	for {
		seen[current] = struct{}{}
		cycle = append(cycle, current)
		next, ok := aliasMaps.Map[current]
		if !ok {
			break
		}
		if _, cycleSeen := seen[next]; cycleSeen {
			largest := cycle[0]
			maxSize := blobSizes[largest]
			for _, n := range cycle {
				if sz := blobSizes[n]; sz > maxSize || (sz == maxSize && n < largest) {
					largest = n
					maxSize = sz
				}
			}
			return largest
		}
		current = next
	}

	if _, ok := rows.Rows[current]; ok {
		return current
	}
	if current != req {
		return current
	}
	return ""
}
