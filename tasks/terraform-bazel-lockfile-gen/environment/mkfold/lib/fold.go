package lib

import (
	"lockkit/internal/types"
)

func FoldGraphX(catalog types.Catalog, policy types.PolicyCtx, roots types.Roots) types.NodeMap {
	nodes := map[string]types.NodeInfo{}
	queue := append([]string{}, roots.Seeds...)
	seen := map[string]bool{}
	for len(queue) > 0 {
		mod := queue[0]
		queue = queue[1:]
		if seen[mod] {
			continue
		}
		pkg, ok := catalog.Packages[mod]
		if !ok {
			continue
		}
		seen[mod] = true
		ver := pkg.Latest
		rawDeps := pkg.Deps[ver]
		for _, edge := range rawDeps {
			name := edge
			if i := indexAt(edge); i >= 0 {
				name = edge[:i]
			}
			queue = append(queue, name)
		}
		nodes[mod] = types.NodeInfo{
			Version: ver,
			Deps:    rawDeps,
		}
	}
	return types.NodeMap{
		EntryID:      roots.EntryID,
		StorageClass: roots.StorageClass,
		Nodes:        nodes,
	}
}

func indexAt(s string) int {
	for i := 0; i < len(s); i++ {
		if s[i] == '@' {
			return i
		}
	}
	return -1
}
