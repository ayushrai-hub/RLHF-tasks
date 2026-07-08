package reconcile

import (
	"claim-weaver/internal/model"
	"claim-weaver/internal/staging"
)

func ValidateExport(snap staging.WeaveSnapshot, final []model.Claim, summary *model.Summary, ledgerPath string) {
	if summary == nil {
		return
	}
	ledger, err := staging.ReadLedger(ledgerPath)
	if err != nil {
		return
	}
	expectedDigest := staging.ErrorsDigest(snap.Errors)
	if ledger.ManifestFingerprint != snap.ManifestFingerprint || ledger.ErrorsDigest != expectedDigest {
		return
	}

	serviceCount := 0
	for _, claim := range final {
		serviceCount += len(claim.ServiceLines)
	}
	summary.ServiceLineCount = serviceCount
	summary.ManifestFingerprint = snap.ManifestFingerprint
	summary.ErrorsDigest = expectedDigest
	summary.ExportEpoch = ledger.ExportEpoch
}
