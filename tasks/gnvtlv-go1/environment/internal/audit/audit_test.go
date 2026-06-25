package audit

import (
	"os"
	"path/filepath"
	"testing"

	"example.com/gnvtlv/internal/decode"
	"example.com/gnvtlv/internal/policy"
	"example.com/gnvtlv/internal/resolve"
)

func readFixture(t *testing.T, name string) []byte {
	t.Helper()
	p := filepath.Join("/app/testdata", name)
	b, err := os.ReadFile(p)
	if err != nil {
		t.Fatalf("read fixture %s: %v", p, err)
	}
	return b
}

func loadAll(t *testing.T, name, policyPath string) (decode.Decoded, resolve.Resolved, *policy.Policy) {
	t.Helper()
	b := readFixture(t, name)
	d, err := decode.Decode(name, b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	reg, err := resolve.LoadRegistries(
		"/app/configs/geneve_registry.json",
		"/app/configs/ethertype_registry.json",
	)
	if err != nil {
		t.Fatalf("registries: %v", err)
	}
	r := resolve.Resolve(d, reg)
	p, err := policy.LoadFromFile(policyPath)
	if err != nil {
		t.Fatalf("policy: %v", err)
	}
	return d, r, p
}

func TestAudit_CleanPacketAccepts(t *testing.T) {
	d, r, p := loadAll(t, "two_clean.bin", "/app/configs/audit_policy.json")
	rep := Audit(d, r, p)
	if rep.Decision != "ACCEPT" {
		t.Fatalf("decision: got %s want ACCEPT", rep.Decision)
	}
}

func TestAudit_CriticalUnknownDrops(t *testing.T) {
	d, r, p := loadAll(t, "unknown_crit.bin", "/app/configs/audit_policy.json")
	rep := Audit(d, r, p)
	if rep.Decision != "DROP" {
		t.Fatalf("decision: got %s want DROP", rep.Decision)
	}
	if !hasPacketCode(rep.PacketFindings, "UNKNOWN_CRITICAL") {
		t.Fatalf("expected UNKNOWN_CRITICAL packet finding, got %+v", rep.PacketFindings)
	}
}

func TestAudit_CriticalUnknownDropsEvenWhenMuted(t *testing.T) {
	d, r, p := loadAll(t, "unknown_crit.bin", "/app/configs/audit_policy_muted.json")
	rep := Audit(d, r, p)
	if rep.Decision != "DROP" {
		t.Fatalf("decision (muted policy): got %s want DROP (cascade overrides mute)", rep.Decision)
	}
	if !rep.OverrideApplied {
		t.Fatalf("expected override_applied=true on muted cascade")
	}
}

func TestAudit_MaxPerClassDrops(t *testing.T) {
	d, r, p := loadAll(t, "three_class_0x0103.bin", "/app/configs/audit_policy_capped.json")
	rep := Audit(d, r, p)
	if rep.Decision != "DROP" {
		t.Fatalf("decision: got %s want DROP", rep.Decision)
	}
	if !hasPacketCode(rep.PacketFindings, "MAX_PER_CLASS") {
		t.Fatalf("expected MAX_PER_CLASS packet finding, got %+v", rep.PacketFindings)
	}
}

func TestAudit_MaxPerClassExactCapAccepts(t *testing.T) {
	d, r, p := loadAll(t, "two_clean.bin", "/app/configs/audit_policy_capped.json")
	rep := Audit(d, r, p)
	if rep.Decision != "ACCEPT" {
		t.Fatalf("decision: got %s want ACCEPT at cap boundary", rep.Decision)
	}
}

func TestAudit_ExperimenterVendorDeniedOnNonAllowlisted(t *testing.T) {
	d, r, p := loadAll(t, "two_experimenters.bin", "/app/configs/audit_policy.json")
	rep := Audit(d, r, p)
	denied := 0
	for _, f := range rep.Findings {
		if f.Code == "EXPERIMENTER_VENDOR_DENIED" {
			denied++
		}
	}
	if denied != 1 {
		t.Fatalf("EXPERIMENTER_VENDOR_DENIED count: got %d want 1 (only opt 1's vendor is non-allowlisted)", denied)
	}
}

func hasPacketCode(pf []PacketFinding, code string) bool {
	for _, f := range pf {
		if f.Code == code {
			return true
		}
	}
	return false
}
