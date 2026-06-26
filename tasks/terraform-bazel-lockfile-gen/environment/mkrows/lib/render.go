package lib

import (
	"lockkit/internal/types"
)

func RenderBlockY(nodeMap types.NodeMap, policy types.PolicyCtx) types.LockSnapshot {
	rows := []types.LockRow{}
	for mod, info := range nodeMap.Nodes {
		rows = append(rows, types.LockRow{
			ModuleID: mod,
			RepoKey:  mod + "/" + info.Version,
			Version:  info.Version,
		})
	}
	return types.LockSnapshot{EntryID: nodeMap.EntryID, Rows: rows}
}
