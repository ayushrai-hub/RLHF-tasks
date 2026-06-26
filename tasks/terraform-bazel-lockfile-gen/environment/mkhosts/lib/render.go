package lib

import (
	"crypto/sha256"
	"encoding/hex"

	"lockkit/internal/types"
)

func RenderBlockZ(nodeMap types.NodeMap, policy types.PolicyCtx) (map[string]any, map[string]any) {
	table := []types.RepoRow{}
	checksum := []types.ChecksumRow{}
	for mod, info := range nodeMap.Nodes {
		key := mod + "/" + info.Version
		table = append(table, types.RepoRow{
			ModuleID: mod,
			RepoKey:  key,
			URL:      "https://default/" + mod,
		})
		raw := sha256.Sum256([]byte(mod + ":" + info.Version))
		checksum = append(checksum, types.ChecksumRow{
			RepoKey: key,
			Digest:  hex.EncodeToString(raw[:]),
		})
	}
	return map[string]any{"rows": table}, map[string]any{"rows": checksum}
}
