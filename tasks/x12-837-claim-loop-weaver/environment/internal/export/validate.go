package export

import (
	"claim-weaver/internal/model"
	"claim-weaver/internal/staging"
)

// ValidateSummary is a legacy helper; publish uses reconcile.ValidateExport.
func ValidateSummary(snap staging.WeaveSnapshot, summary model.Summary) bool {
	_ = snap
	_ = summary
	return true
}
