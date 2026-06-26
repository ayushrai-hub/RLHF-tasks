package stages

import (
	chainlib "lockkit/mkchain/lib"
	statelib "lockkit/mkstate/lib"
	"lockkit/internal/types"
)

func Hydrate(entry string, roots types.Roots) (types.NodeMap, bool) {
	if tail, hasTail := statelib.ReadReplayTail(); hasTail && tail.EntryID != entry {
		return types.NodeMap{}, false
	}
	if !chainlib.ValidateChainPrefixChain() {
		return types.NodeMap{}, false
	}
	cached, ok := statelib.LoadCached(entry, roots)
	if !ok {
		return types.NodeMap{}, false
	}
	if tail, hasTail := statelib.ReadReplayTail(); hasTail {
		if tail.SeedDigest != statelib.SeedDigestFor(roots) {
			return types.NodeMap{}, false
		}
		if slot, ok := statelib.ReadSlot(entry); ok && tail.LinkDigest != slot.LinkDigest {
			return types.NodeMap{}, false
		}
		if tail.Gen != statelib.ReadReplayGen() {
			return types.NodeMap{}, false
		}
		if !chainlib.ChainHeadMatches(entry, statelib.ReadReplayGen()) {
			return types.NodeMap{}, false
		}
	}
	cached.EntryID = entry
	cached.StorageClass = roots.StorageClass
	return cached, true
}
