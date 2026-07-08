package weave

import "claim-weaver/internal/model"

func ApplySupersession(claims []model.Claim) []model.Claim {
	remove := make(map[string]struct{})
	for _, claim := range claims {
		if claim.FrequencyCode == "7" && claim.RefF8 != "" {
			remove[claim.RefF8] = struct{}{}
		}
	}
	out := make([]model.Claim, 0, len(claims))
	for _, claim := range claims {
		if _, drop := remove[claim.ControlNumber]; drop {
			continue
		}
		claim.RefF8 = ""
		out = append(out, claim)
	}
	return out
}
