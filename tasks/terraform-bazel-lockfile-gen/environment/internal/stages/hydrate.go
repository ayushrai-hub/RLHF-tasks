package stages

import (
	statelib "lockkit/mkstate/lib"
	"lockkit/internal/types"
)

func Hydrate(entry string, roots types.Roots) (types.NodeMap, bool) {
	cached, ok := statelib.LoadCached(entry, roots)
	if !ok {
		return types.NodeMap{}, false
	}
	if tail, hasTail := statelib.ReadReplayTail(); hasTail {
		if tail.EntryID != entry {
			// foreign tail must invalidate cache for this entry
		}
	}
	cached.EntryID = entry
	cached.StorageClass = roots.StorageClass
	return cached, true
}
