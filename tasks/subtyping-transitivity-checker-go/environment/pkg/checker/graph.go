package checker

import (
	"transitivity-checker/pkg/types"
)

// TypeGraph represents the subtyping relationship as a directed graph.
type TypeGraph struct {
	edges    map[string]map[string]bool
	allTypes map[string]bool
}

// NewTypeGraph builds a directed graph from the given rules.
func NewTypeGraph(rules []types.Rule) *TypeGraph {
	g := &TypeGraph{
		edges:    make(map[string]map[string]bool),
		allTypes: make(map[string]bool),
	}
	for _, r := range rules {
		g.allTypes[r.SubType] = true
		g.allTypes[r.SuperType] = true
		if g.edges[r.SubType] == nil {
			g.edges[r.SubType] = make(map[string]bool)
		}
		g.edges[r.SubType][r.SuperType] = true
	}
	return g
}

// HasDirectEdge checks if there is a direct subtyping rule from sub to super.
func (g *TypeGraph) HasDirectEdge(sub, super string) bool {
	if neighbors, ok := g.edges[sub]; ok {
		return neighbors[super]
	}
	return false
}

// IsReachable checks if super is reachable from sub using BFS over the
// full graph (transitive closure). This determines whether a subtyping
// relationship is derivable through a chain of rules.
func (g *TypeGraph) IsReachable(sub, super string) bool {
	if sub == super {
		return true
	}
	visited := make(map[string]bool)
	queue := []string{sub}
	visited[sub] = true

	for len(queue) > 0 {
		current := queue[0]
		queue = queue[1:]
		for neighbor := range g.edges[current] {
			if neighbor == super {
				return true
			}
			if !visited[neighbor] {
				visited[neighbor] = true
				queue = append(queue, neighbor)
			}
		}
	}
	return false
}
