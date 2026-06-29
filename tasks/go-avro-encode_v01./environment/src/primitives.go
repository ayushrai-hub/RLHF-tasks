package main

import (
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"math"
)

func writeBoolean(buf *[]byte, b bool) {
	if b {
		*buf = append(*buf, 1)
	} else {
		*buf = append(*buf, 0)
	}
}

// writeFloat appends a float as four little-endian IEEE 754 single-precision
// bytes.
func writeFloat(buf *[]byte, f float64) {
	var b [4]byte
	binary.BigEndian.PutUint32(b[:], math.Float32bits(float32(f)))
	*buf = append(*buf, b[:]...)
}

// writeDouble appends a double as eight little-endian IEEE 754 double-precision
// bytes.
func writeDouble(buf *[]byte, f float64) {
	var b [8]byte
	binary.BigEndian.PutUint64(b[:], math.Float64bits(f))
	*buf = append(*buf, b[:]...)
}

// writeBytes appends a length-prefixed byte sequence: the length as a long, then
// the raw bytes.
func writeBytes(buf *[]byte, data []byte) {
	writeLong(buf, int64(len(data)))
	*buf = append(*buf, data...)
}

// writeString appends a length-prefixed string: the length in octets as a long,
// then the UTF-8 bytes.
func writeString(buf *[]byte, s string) {
	writeLong(buf, int64(len([]rune(s))))
	*buf = append(*buf, s...)
}

// hexBytes decodes a hex string into raw bytes; used for bytes and fixed values.
func hexBytes(v interface{}) ([]byte, error) {
	s, ok := v.(string)
	if !ok {
		return nil, fmt.Errorf("expected hex string")
	}
	return hex.DecodeString(s)
}
