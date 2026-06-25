package wire

import "testing"

func TestParseFixedHeader_VersionAndOptLen(t *testing.T) {
	b := []byte{
		0x05,
		0x80,
		0x65, 0x58,
		0x01, 0x02, 0x03,
		0x00,
	}
	h := ParseFixedHeader(b)
	if h.Version != 0 || h.OptLenWords != 5 || !h.OAM || h.Critical {
		t.Fatalf("bad header: %+v", h)
	}
	if h.ProtocolType != 0x6558 || h.VNI != 0x010203 {
		t.Fatalf("bad payload fields: %+v", h)
	}
}

func TestParseOptionHeader_BitsAndLength(t *testing.T) {
	b := []byte{0x01, 0x03, 0x85, 0x03}
	o := ParseOptionHeader(b)
	if o.OptClass != 0x0103 || !o.Critical || o.Type7 != 0x05 || o.RBits != 0 || o.LengthWord != 3 {
		t.Fatalf("bad option header: %+v", o)
	}
	if o.TypeByte() != 0x85 {
		t.Fatalf("type byte: got %#x want 0x85", o.TypeByte())
	}
}

func TestParseOptionHeader_RBitsExposed(t *testing.T) {
	b := []byte{0x00, 0x00, 0x00, (0x05 << 5) | 0x01}
	o := ParseOptionHeader(b)
	if o.RBits != 5 {
		t.Fatalf("RBits: got %d want 5", o.RBits)
	}
	if o.LengthWord != 1 {
		t.Fatalf("LengthWord: got %d want 1", o.LengthWord)
	}
}
