package decode

import (
	"os"
	"path/filepath"
	"testing"
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

func TestDecode_BareHeaderNoOptions(t *testing.T) {
	b := readFixture(t, "bare_header.bin")
	d, err := Decode("bare_header.bin", b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	if d.Header.OptLenWords != 0 {
		t.Fatalf("OptLenWords: got %d want 0", d.Header.OptLenWords)
	}
	if len(d.Options) != 0 {
		t.Fatalf("options: got %d want 0", len(d.Options))
	}
	if len(d.Errors) != 0 {
		t.Fatalf("errors: got %d want 0 (%v)", len(d.Errors), d.Errors)
	}
}

func TestDecode_TwoCleanOptions(t *testing.T) {
	b := readFixture(t, "two_clean.bin")
	d, err := Decode("two_clean.bin", b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(d.Options) != 2 {
		t.Fatalf("options: got %d want 2", len(d.Options))
	}
	if d.Options[0].OptClass != 0x0103 || d.Options[0].Type != 0x05 {
		t.Fatalf("option[0]: got class=%#x type=%#x", d.Options[0].OptClass, d.Options[0].Type)
	}
	if d.Options[1].OptClass != 0x0103 || d.Options[1].Type != 0x06 {
		t.Fatalf("option[1]: got class=%#x type=%#x", d.Options[1].OptClass, d.Options[1].Type)
	}
	if len(d.Errors) != 0 {
		t.Fatalf("errors: got %d want 0 (%v)", len(d.Errors), d.Errors)
	}
}

func TestDecode_RBitsNonzeroReported(t *testing.T) {
	b := readFixture(t, "rbits_nonzero.bin")
	d, err := Decode("rbits_nonzero.bin", b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	if !hasErr(d.Errors, "OPT_R_BITS_NONZERO") {
		t.Fatalf("expected OPT_R_BITS_NONZERO in errors, got %+v", d.Errors)
	}
}

func TestDecode_OptLenOverrun(t *testing.T) {
	b := readFixture(t, "opt_len_overrun.bin")
	d, err := Decode("opt_len_overrun.bin", b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	if !hasErr(d.Errors, "OPT_LEN_OVERRUN") {
		t.Fatalf("expected OPT_LEN_OVERRUN in errors, got %+v", d.Errors)
	}
}

func TestDecode_VersionNonzero(t *testing.T) {
	b := readFixture(t, "version_one.bin")
	d, err := Decode("version_one.bin", b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	if !hasErr(d.Errors, "VERSION_NONZERO") {
		t.Fatalf("expected VERSION_NONZERO, got %+v", d.Errors)
	}
}

func hasErr(errs []Error, code string) bool {
	for _, e := range errs {
		if e.Code == code {
			return true
		}
	}
	return false
}
