package export

import (
	"claim-weaver/internal/model"
	"claim-weaver/internal/reconcile"
	"claim-weaver/internal/staging"
)

func Publish(snap staging.WeaveSnapshot) (model.WovenOutput, model.Summary) {
	paths := staging.ResolveStatePaths()
	return reconcile.Build(snap, paths.Ledger)
}
