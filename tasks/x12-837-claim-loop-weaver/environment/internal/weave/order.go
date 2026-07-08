package weave

import (
	"claim-weaver/internal/model"
	"sort"
)

func SortServiceLines(lines []model.ServiceLine) []model.ServiceLine {
	out := append([]model.ServiceLine(nil), lines...)
	sort.Slice(out, func(i, j int) bool {
		return out[i].LXSequence < out[j].LXSequence
	})
	return out
}

func SortClaims(claims []model.Claim) []model.Claim {
	out := append([]model.Claim(nil), claims...)
	sort.Slice(out, func(i, j int) bool {
		return out[i].ControlNumber < out[j].ControlNumber
	})
	return out
}
