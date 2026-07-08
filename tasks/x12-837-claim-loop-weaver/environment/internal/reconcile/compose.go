package reconcile

import (
	"fmt"
	"sort"

	"claim-weaver/internal/model"
	"claim-weaver/internal/staging"
	"claim-weaver/internal/weave"
)

// ComposeDraft maps snapshot staging rows to claim objects before supersession.
func ComposeDraft(snap staging.WeaveSnapshot) []model.Claim {
	rawClaims := make([]model.Claim, 0, len(snap.Claims))

	for _, claimSnap := range snap.Claims {
		compSep := byte(':')

		lines := make([]model.ServiceLine, 0)
		inherited := []string{}
		keys := make([]int, 0, len(claimSnap.Lines))
		for lx := range claimSnap.Lines {
			keys = append(keys, lx)
		}
		sort.Ints(keys)
		for _, lx := range keys {
			line := claimSnap.Lines[lx]
			if line.SV1Fields == nil {
				continue
			}
			pointers := ResolvePointers(line.SV1Fields, inherited, compSep)
			lines = append(lines, model.ServiceLine{
				LXSequence:        lx,
				Procedure:         weave.ParseProcedure(line.SV1Fields, compSep),
				Charge:            formatMoney(fieldAt(line.SV1Fields, 2, "0")),
				DiagnosisPointers: pointers,
			})
			if len(line.HICodes) > 0 {
				inherited = make([]string, len(line.HICodes))
				for i := range line.HICodes {
					inherited[i] = fmt.Sprintf("%d", i+1)
				}
			}
		}
		rawClaims = append(rawClaims, model.Claim{
			ControlNumber: claimSnap.ControlNumber,
			PatientName:   claimSnap.PatientName,
			SubscriberID:  claimSnap.SubscriberID,
			TotalCharge:   formatMoney(fieldAt(claimSnap.CLMFields, 2, "0")),
			FrequencyCode: parseFrequency(claimSnap.CLMFields, compSep),
			RefF8:         claimSnap.RefF8,
			ServiceLines:  weave.SortServiceLines(lines),
		})
	}

	return rawClaims
}
