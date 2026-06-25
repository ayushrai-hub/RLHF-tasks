package audit

import (
	"fmt"

	"example.com/gnvtlv/internal/policy"
	"example.com/gnvtlv/internal/resolve"
)

func CascadeApplyUnknownCritical(r resolve.Resolved, p *policy.Policy, currentDecision string) (PacketFinding, string, bool) {
	idx := -1
	for _, o := range r.Options {
		if !o.Recognized && o.Critical {
			idx = o.Index
			break
		}
	}
	if idx < 0 {
		return PacketFinding{}, currentDecision, false
	}
	muted := p.IsMuted("UNKNOWN_CRITICAL")
	pf := PacketFinding{
		Code:            "UNKNOWN_CRITICAL",
		Severity:        "error",
		Message:         fmt.Sprintf("critical+unknown option at index %d forces DROP per §X.2", idx),
		Muted:           muted,
		OverrideApplied: muted,
	}
	return pf, "DROP", true
}

func CascadeApplyMaxPerClass(r resolve.Resolved, p *policy.Policy, currentDecision string) ([]PacketFinding, string) {
	counts := make(map[int]int)
	for _, o := range r.Options {
		counts[o.OptClass]++
	}
	out := make([]PacketFinding, 0)
	dec := currentDecision
	for class, n := range counts {
		limit := p.CapForClass(class)
		if limit == 0 {
			continue
		}
		if n > limit {
			muted := p.IsMuted("MAX_PER_CLASS")
			out = append(out, PacketFinding{
				Code:     "MAX_PER_CLASS",
				Severity: "error",
				Message:  fmt.Sprintf("opt_class=%#x count=%d exceeds cap=%d", class, n, limit),
				Muted:    muted,
			})
			if !muted {
				dec = "DROP"
			}
		}
	}
	return out, dec
}
