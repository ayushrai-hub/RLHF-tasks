package export

import (
	"claim-weaver/internal/model"
	"claim-weaver/internal/staging"
)

// ComposeFromSnapshot is a legacy helper; publish uses reconcile.ComposeDraft.
func ComposeFromSnapshot(snap staging.WeaveSnapshot) []model.Claim {
	_ = snap
	return nil
}
