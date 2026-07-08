package reconcile

import (
	"strings"

	"claim-weaver/internal/model"
	"claim-weaver/internal/staging"
	"claim-weaver/internal/weave"
)

func Build(snap staging.WeaveSnapshot, ledgerPath string) (model.WovenOutput, model.Summary) {
	rawClaims := ComposeDraft(snap)
	final := ApplySupersession(weave.SortClaims(rawClaims))
	summary := model.Summary{
		ClaimCount:      len(final),
		SkippedSegments: snap.Skipped,
	}
	ValidateExport(snap, final, &summary, ledgerPath)
	return model.WovenOutput{Claims: final}, summary
}

func fieldAt(fields []string, idx int, fallback string) string {
	if len(fields) <= idx || fields[idx] == "" {
		return fallback
	}
	return fields[idx]
}

func parseFrequency(fields []string, compSep byte) string {
	if len(fields) <= 5 || fields[5] == "" {
		return "1"
	}
	parts := strings.Split(fields[5], string([]byte{compSep}))
	if len(parts) >= 3 && parts[2] != "" {
		return parts[2]
	}
	return "1"
}

func formatMoney(value string) string {
	if !strings.Contains(value, ".") {
		return value + ".00"
	}
	parts := strings.SplitN(value, ".", 2)
	frac := parts[1]
	if len(frac) < 2 {
		frac += strings.Repeat("0", 2-len(frac))
	} else if len(frac) > 2 {
		frac = frac[:2]
	}
	return parts[0] + "." + frac
}
