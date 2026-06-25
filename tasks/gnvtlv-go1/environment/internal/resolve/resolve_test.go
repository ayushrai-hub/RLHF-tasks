package resolve

import (
	"os"
	"path/filepath"
	"testing"

	"example.com/gnvtlv/internal/decode"
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

func loadReg(t *testing.T) *Registries {
	t.Helper()
	r, err := LoadRegistries(
		"/app/configs/geneve_registry.json",
		"/app/configs/ethertype_registry.json",
	)
	if err != nil {
		t.Fatalf("load registries: %v", err)
	}
	return r
}

func TestResolve_KnownOptionsAreRecognized(t *testing.T) {
	r := loadReg(t)
	b := readFixture(t, "two_clean.bin")
	d, err := decode.Decode("two_clean.bin", b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	res := Resolve(d, r)
	if len(res.Options) != 2 {
		t.Fatalf("options: got %d want 2", len(res.Options))
	}
	for i, o := range res.Options {
		if !o.Recognized {
			t.Fatalf("option[%d] not recognized; reg should know class=%#x type=%#x", i, o.OptClass, o.Type)
		}
		if o.Name == "" || o.Kind == "unknown" {
			t.Fatalf("option[%d] missing name/kind: %+v", i, o)
		}
	}
}

func TestResolve_HeaderProtocolNameFilled(t *testing.T) {
	r := loadReg(t)
	b := readFixture(t, "two_clean.bin")
	d, err := decode.Decode("two_clean.bin", b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	res := Resolve(d, r)
	if res.Header.ProtocolTypeName == "" {
		t.Fatalf("ProtocolTypeName empty; expected resolved name for %#x", res.Header.ProtocolType)
	}
}

func TestResolve_UnknownCriticalUnrecognized(t *testing.T) {
	r := loadReg(t)
	b := readFixture(t, "unknown_crit.bin")
	d, err := decode.Decode("unknown_crit.bin", b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	res := Resolve(d, r)
	if len(res.Options) != 1 {
		t.Fatalf("options: got %d want 1", len(res.Options))
	}
	o := res.Options[0]
	if o.Recognized {
		t.Fatalf("option should be unrecognized")
	}
	if !o.Critical {
		t.Fatalf("option should be critical")
	}
}

func TestResolve_LengthMismatchIssue(t *testing.T) {
	r := loadReg(t)
	b := readFixture(t, "length_mismatch.bin")
	d, err := decode.Decode("length_mismatch.bin", b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	res := Resolve(d, r)
	found := false
	for _, is := range res.Issues {
		if is.Code == "OPT_LENGTH_MISMATCH" {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected OPT_LENGTH_MISMATCH issue, got %+v", res.Issues)
	}
}
