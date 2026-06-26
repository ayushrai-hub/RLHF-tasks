package stages

import (
	foldlib "lockkit/mkfold/lib"
	statelib "lockkit/mkstate/lib"
	"lockkit/internal/types"
)

func Resolve(catalog types.Catalog, policy types.PolicyCtx, roots types.Roots) types.NodeMap {
	return foldlib.FoldGraphX(catalog, policy, roots)
}

func Persist(nodeMap types.NodeMap, roots types.Roots) {
	_ = statelib.SaveLedger(nodeMap, roots)
}
