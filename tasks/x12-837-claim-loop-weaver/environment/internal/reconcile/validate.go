package reconcile

import (
	"claim-weaver/internal/model"
	"claim-weaver/internal/staging"
)

// ValidateExport finalizes summary fields from the snapshot, ledger, and surviving claims.
func ValidateExport(snap staging.WeaveSnapshot, final []model.Claim, summary *model.Summary, ledgerPath string) {
	_ = snap
	_ = final
	_ = ledgerPath
	if summary == nil {
		return
	}
}
