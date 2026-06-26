package lib

import (
	"sort"

	"lockkit/internal/types"
)

func rowKey(row types.LockRow) (string, string) {
	return row.ModuleID, row.RepoKey
}

func RenderBlockY(nodeMap types.NodeMap, policy types.PolicyCtx) types.LockSnapshot {
	if len(nodeMap.Nodes) == 0 {
		return types.LockSnapshot{EntryID: nodeMap.EntryID, Rows: []types.LockRow{}}
	}
	mods := make([]string, 0, len(nodeMap.Nodes))
	for mod := range nodeMap.Nodes {
		mods = append(mods, mod)
	}
	sort.Strings(mods)
	rows := make([]types.LockRow, 0, len(mods))
	for _, mod := range mods {
		version := nodeMap.Nodes[mod].Version
		rows = append(rows, types.LockRow{
			ModuleID: mod,
			RepoKey:  mod + "/" + version,
			Version:  version,
		})
	}
	sort.Slice(rows, func(i, j int) bool {
		am, ar := rowKey(rows[i])
		bm, br := rowKey(rows[j])
		if am != bm {
			return am < bm
		}
		return ar < br
	})
	return types.LockSnapshot{EntryID: nodeMap.EntryID, Rows: rows}
}
