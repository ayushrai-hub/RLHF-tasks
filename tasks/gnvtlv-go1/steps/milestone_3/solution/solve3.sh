#!/bin/bash
set -euo pipefail
cd /app

echo "==> read the cascade-rule sections that govern this milestone"
sed -n '18,53p' /app/docs/CASCADE_RULES.md
echo "==> inspect the cascade helpers already in place"
grep -n '^func ' /app/internal/audit/cascade.go
echo "==> inspect the audit policy variants"
ls /app/configs/audit_policy*.json
sed -n '1,4p' /app/configs/audit_policy_muted.json
sed -n '1,8p' /app/configs/audit_policy_capped.json

echo "==> rewrite audit.go to wire the cascade helpers + override flag"
cat > /app/internal/audit/audit.go <<'GOEOF'
package audit

import (
	"encoding/binary"
	"encoding/hex"
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
				OptIndex: e.OptIndex, Code: e.Code, Severity: "error",
				Message: e.Message, Muted: p.IsMuted(e.Code),
			})
			continue
		}
		muted := p.IsMuted(e.Code)
		rep.PacketFindings = append(rep.PacketFindings, PacketFinding{
			Code: e.Code, Severity: "error", Message: e.Message,
			Muted: muted, OverrideApplied: false,
		})
		if !muted {
			rep.Decision = "DROP"
		}
	}

	if !r.Header.OAM {
		if pf, dec, fired := CascadeApplyUnknownCritical(r, p, rep.Decision); fired {
			rep.PacketFindings = append(rep.PacketFindings, pf)
			rep.Decision = dec
			if pf.OverrideApplied {
				rep.OverrideApplied = true
			}
		}
	}

	caps, dec := CascadeApplyMaxPerClass(r, p, rep.Decision)
	rep.PacketFindings = append(rep.PacketFindings, caps...)
	rep.Decision = dec

	for _, o := range r.Options {
		if o.OptClass < 0xFF00 || o.OptClass > 0xFFFF {
			continue
		}
		payload, _ := hex.DecodeString(o.DataHex)
		if len(payload) < 4 {
			continue
		}
		vendor := int(binary.BigEndian.Uint32(payload[:4]))
		if !p.VendorAllowed(vendor) {
			rep.Findings = append(rep.Findings, Finding{
				OptIndex: o.Index,
				Code:     "EXPERIMENTER_VENDOR_DENIED",
				Severity: "error",
				Message:  fmt.Sprintf("option %d vendor=%#x not in allowlist", o.Index, vendor),
				Muted:    p.IsMuted("EXPERIMENTER_VENDOR_DENIED"),
			})
		}
	}

	for _, is := range r.Issues {
		rep.Findings = append(rep.Findings, Finding{
			OptIndex: is.OptIndex, Code: is.Code,
			Severity: "warning", Message: is.Message,
			Muted: p.IsMuted(is.Code),
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
GOEOF

echo "==> verify the cascade wiring landed"
grep -n 'CascadeApplyUnknownCritical(r, p, rep.Decision)' /app/internal/audit/audit.go
grep -n 'CascadeApplyMaxPerClass(r, p, rep.Decision)' /app/internal/audit/audit.go

if ! grep -qF 'CascadeApplyUnknownCritical(r, p, rep.Decision)' /app/internal/audit/audit.go; then
    echo "M3 oracle: cascade wiring did not land in audit.go" >&2
    exit 1
fi
if ! grep -qF 'CascadeApplyMaxPerClass(r, p, rep.Decision)' /app/internal/audit/audit.go; then
    echo "M3 oracle: per-class cap wiring did not land in audit.go" >&2
    exit 1
fi

echo "==> build and run the full test suite"
mkdir -p /app/bin
go build -o /app/bin/gnvtlv ./cmd/gnvtlv
go build ./...
go test ./...
