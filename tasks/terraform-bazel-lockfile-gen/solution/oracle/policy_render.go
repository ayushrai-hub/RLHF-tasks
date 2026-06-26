package lib

import (
	"crypto/sha256"
	"encoding/hex"
	"sort"
	"strings"

	"lockkit/internal/types"
)

func repoFor(mod string, info types.NodeInfo, packages map[string]types.Package, aliases map[string]string, storage, policyText string) string {
	repo := "https://default/" + mod
	if pkg, ok := packages[mod]; ok && pkg.Repo != "" {
		repo = pkg.Repo
	}
	if storage == "legacy" && mod == "mod_legacy" && strings.Contains(policyText, "legacy") {
		if alias, ok := aliases["legacy_mirror"]; ok {
			return alias
		}
	}
	return repo
}

func digestFor(mod string, info types.NodeInfo, packages map[string]types.Package) string {
	if pkg, ok := packages[mod]; ok && pkg.Checksum != "" {
		return pkg.Checksum
	}
	raw := sha256.Sum256([]byte(mod + ":" + info.Version))
	return hex.EncodeToString(raw[:])
}

func RenderBlockZ(nodeMap types.NodeMap, policy types.PolicyCtx) (map[string]any, map[string]any) {
	table := []types.RepoRow{}
	checksum := []types.ChecksumRow{}
	mods := make([]string, 0, len(nodeMap.Nodes))
	for mod := range nodeMap.Nodes {
		mods = append(mods, mod)
	}
	sort.Strings(mods)
	for _, mod := range mods {
		info := nodeMap.Nodes[mod]
		key := mod + "/" + info.Version
		table = append(table, types.RepoRow{
			ModuleID: mod,
			RepoKey:  key,
			URL:      repoFor(mod, info, policy.Packages, policy.Aliases, nodeMap.StorageClass, policy.Text),
		})
		checksum = append(checksum, types.ChecksumRow{
			RepoKey: key,
			Digest:  digestFor(mod, info, policy.Packages),
		})
	}
	sort.Slice(table, func(i, j int) bool {
		if table[i].ModuleID != table[j].ModuleID {
			return table[i].ModuleID < table[j].ModuleID
		}
		return table[i].RepoKey < table[j].RepoKey
	})
	sort.Slice(checksum, func(i, j int) bool {
		return checksum[i].RepoKey < checksum[j].RepoKey
	})
	return map[string]any{"rows": table}, map[string]any{"rows": checksum}
}
