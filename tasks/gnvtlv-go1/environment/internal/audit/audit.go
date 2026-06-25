package audit

import (
	"fmt"

	"example.com/gnvtlv/internal/decode"
	"example.com/gnvtlv/internal/policy"
	"example.com/gnvtlv/internal/resolve"
)

type Report struct {
	Source            string          `json:"source"`
	Decision          string          `json:"decision"`
	OverrideApplied   bool            `json:"override_applied"`
	Findings          []Finding       `json:"findings"`
	PacketFindings    []PacketFinding `json:"packet_findings"`
	OptionsTotal      int             `json:"options_total"`
	OptionsRecognized int             `json:"options_recognized"`
}

type Finding struct {
	OptIndex int    `json:"opt_index"`
	Code     string `json:"code"`
	Severity string `json:"severity"`
	Message  string `json:"message"`
	Muted    bool   `json:"muted"`
}

type PacketFinding struct {
	Code            string `json:"code"`
	Severity        string `json:"severity"`
	Message         string `json:"message"`
	Muted           bool   `json:"muted"`
	OverrideApplied bool   `json:"override_applied"`
}

func Audit(d decode.Decoded, r resolve.Resolved, p *policy.Policy) Report {
	rep := Report{
		Source:            r.Source,
		Decision:          "ACCEPT",
		OverrideApplied:   false,
		Findings:          make([]Finding, 0),
		PacketFindings:    make([]PacketFinding, 0),
		OptionsTotal:      len(r.Options),
		OptionsRecognized: countRecognized(r),
	}

	for _, e := range r.DecodeErrors {
		if e.OptIndex >= 0 {
			rep.Findings = append(rep.Findings, Finding{
				OptIndex: e.OptIndex,
				Code:     e.Code,
				Severity: "error",
				Message:  e.Message,
				Muted:    p.IsMuted(e.Code),
			})
			continue
		}
		muted := p.IsMuted(e.Code)
		rep.PacketFindings = append(rep.PacketFindings, PacketFinding{
			Code: e.Code, Severity: "error", Message: e.Message,
			Muted:           muted,
			OverrideApplied: false,
		})
		if !muted {
			rep.Decision = "DROP"
		}
	}

	for _, o := range r.Options {
		if !o.Recognized && o.Critical {
			muted := p.IsMuted("UNKNOWN_CRITICAL")
			rep.Findings = append(rep.Findings, Finding{
				OptIndex: o.Index,
				Code:     "UNKNOWN_CRITICAL",
				Severity: "error",
				Message:  fmt.Sprintf("option %d class=%#x type=%#x critical+unknown", o.Index, o.OptClass, o.Type),
				Muted:    muted,
			})
			_ = muted
		}
	}

	for _, is := range r.Issues {
		rep.Findings = append(rep.Findings, Finding{
			OptIndex: is.OptIndex,
			Code:     is.Code,
			Severity: "warning",
			Message:  is.Message,
			Muted:    p.IsMuted(is.Code),
		})
	}

	_ = d
	return rep
}

func countRecognized(r resolve.Resolved) int {
	n := 0
	for _, o := range r.Options {
		if o.Recognized {
			n++
		}
	}
	return n
}
