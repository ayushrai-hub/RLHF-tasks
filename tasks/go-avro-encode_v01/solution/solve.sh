#!/usr/bin/env bash
set -eu
cd /app

# Read the contract, look at the modules to change, build, and run the samples.
sed -n '1,200p' docs/format.md
sed -n '1,200p' docs/spec.md
for m in varint primitives complex encoder; do echo "--- src/$m.go ---"; cat "src/$m.go"; done
go build -o /tmp/avroencode ./src
for f in examples/*.in.json; do echo "--- $f ---"; /tmp/avroencode < "$f"; done

# Bring each module in line with the Avro binary encoding.

cat > src/varint.go <<'GO_EOF'
package main

// writeVarint appends the unsigned variable-length encoding of u: seven bits per
// byte, least significant group first, with the high bit set on every byte
// except the last.
func writeVarint(buf *[]byte, u uint64) {
	for u >= 0x80 {
		*buf = append(*buf, byte(u)|0x80)
		u >>= 7
	}
	*buf = append(*buf, byte(u))
}

// writeLong appends an Avro int or long: the value is zig-zag mapped so small
// magnitudes stay short, then written as an unsigned varint.
func writeLong(buf *[]byte, n int64) {
	zz := uint64((n << 1) ^ (n >> 63))
	writeVarint(buf, zz)
}
GO_EOF

cat > src/primitives.go <<'GO_EOF'
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
	binary.LittleEndian.PutUint32(b[:], math.Float32bits(float32(f)))
	*buf = append(*buf, b[:]...)
}

// writeDouble appends a double as eight little-endian IEEE 754 double-precision
// bytes.
func writeDouble(buf *[]byte, f float64) {
	var b [8]byte
	binary.LittleEndian.PutUint64(b[:], math.Float64bits(f))
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
	writeLong(buf, int64(len(s)))
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
GO_EOF

cat > src/complex.go <<'GO_EOF'
package main

import (
	"fmt"
	"sort"
)

// writeRecord encodes a record: each field value in the schema's declared field
// order, concatenated with no framing.
func writeRecord(buf *[]byte, fields []Field, v interface{}) error {
	m, ok := v.(map[string]interface{})
	if !ok {
		return fmt.Errorf("expected record object")
	}
	for _, f := range fields {
		fv, ok := m[f.Name]
		if !ok {
			return fmt.Errorf("missing field %q", f.Name)
		}
		if err := encodeValue(buf, f.Type, fv); err != nil {
			return err
		}
	}
	return nil
}

// writeArray encodes an array as a single block of items: a positive item count
// as a long, the items, and a terminating zero-count block. An empty array is
// just the zero block.
func writeArray(buf *[]byte, items *Schema, v interface{}) error {
	arr, ok := v.([]interface{})
	if !ok {
		return fmt.Errorf("expected array")
	}
	if len(arr) > 0 {
		writeLong(buf, int64(len(arr)))
		for _, it := range arr {
			if err := encodeValue(buf, items, it); err != nil {
				return err
			}
		}
	}
	writeLong(buf, 0)
	return nil
}

// writeMap encodes a map like an array whose items are key then value. Members
// are written in ascending order of their key bytes. The block is terminated by
// a zero count.
func writeMap(buf *[]byte, values *Schema, v interface{}) error {
	m, ok := v.(map[string]interface{})
	if !ok {
		return fmt.Errorf("expected map object")
	}
	if len(m) > 0 {
		keys := make([]string, 0, len(m))
		for k := range m {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		writeLong(buf, int64(len(m)))
		for _, k := range keys {
			writeString(buf, k)
			if err := encodeValue(buf, values, m[k]); err != nil {
				return err
			}
		}
	}
	writeLong(buf, 0)
	return nil
}

// writeEnum encodes an enum as the zero-based position of its symbol in the
// schema's symbol list.
func writeEnum(buf *[]byte, symbols []string, v interface{}) error {
	s, ok := v.(string)
	if !ok {
		return fmt.Errorf("expected enum symbol")
	}
	for i, sym := range symbols {
		if sym == s {
			writeLong(buf, int64(i))
			return nil
		}
	}
	return fmt.Errorf("symbol %q not in enum", s)
}

// writeUnion encodes a union as the zero-based branch index, then the value
// against that branch. A null value selects the null branch; any other value is
// the wrapper object {"<branch>": value}.
func writeUnion(buf *[]byte, branches []*Schema, v interface{}) error {
	if v == nil {
		for i, b := range branches {
			if b.Type == "null" {
				writeLong(buf, int64(i))
				return nil
			}
		}
		return fmt.Errorf("null not in union")
	}
	m, ok := v.(map[string]interface{})
	if !ok || len(m) != 1 {
		return fmt.Errorf("expected union wrapper object")
	}
	var name string
	var inner interface{}
	for k, val := range m {
		name, inner = k, val
	}
	for i, b := range branches {
		if branchName(b) == name {
			writeLong(buf, int64(i))
			return encodeValue(buf, b, inner)
		}
	}
	return fmt.Errorf("branch %q not in union", name)
}

func branchName(s *Schema) string {
	switch s.Type {
	case "record", "enum", "fixed":
		return s.Name
	default:
		return s.Type
	}
}
GO_EOF

cat > src/encoder.go <<'GO_EOF'
package main

import (
	"encoding/json"
	"fmt"
)

// encode produces the Avro binary encoding of v against schema s.
func encode(s *Schema, v interface{}) ([]byte, error) {
	var buf []byte
	if err := encodeValue(&buf, s, v); err != nil {
		return nil, err
	}
	return buf, nil
}

// encodeValue appends the encoding of v against schema s to buf.
func encodeValue(buf *[]byte, s *Schema, v interface{}) error {
	switch s.Type {
	case "null":
		if v != nil {
			return fmt.Errorf("expected null")
		}
		return nil
	case "boolean":
		b, ok := v.(bool)
		if !ok {
			return fmt.Errorf("expected boolean")
		}
		writeBoolean(buf, b)
		return nil
	case "int", "long":
		n, err := asInt64(v)
		if err != nil {
			return err
		}
		writeLong(buf, n)
		return nil
	case "float":
		f, err := asFloat(v)
		if err != nil {
			return err
		}
		writeFloat(buf, f)
		return nil
	case "double":
		f, err := asFloat(v)
		if err != nil {
			return err
		}
		writeDouble(buf, f)
		return nil
	case "bytes":
		data, err := hexBytes(v)
		if err != nil {
			return err
		}
		writeBytes(buf, data)
		return nil
	case "string":
		str, ok := v.(string)
		if !ok {
			return fmt.Errorf("expected string")
		}
		writeString(buf, str)
		return nil
	case "fixed":
		data, err := hexBytes(v)
		if err != nil {
			return err
		}
		if len(data) != s.Size {
			return fmt.Errorf("fixed length mismatch")
		}
		*buf = append(*buf, data...)
		return nil
	case "enum":
		return writeEnum(buf, s.Symbols, v)
	case "record":
		return writeRecord(buf, s.Fields, v)
	case "array":
		return writeArray(buf, s.Items, v)
	case "map":
		return writeMap(buf, s.Values, v)
	case "union":
		return writeUnion(buf, s.Branches, v)
	}
	return fmt.Errorf("unknown schema type %q", s.Type)
}

func asInt64(v interface{}) (int64, error) {
	n, ok := v.(json.Number)
	if !ok {
		return 0, fmt.Errorf("expected integer")
	}
	return n.Int64()
}

func asFloat(v interface{}) (float64, error) {
	n, ok := v.(json.Number)
	if !ok {
		return 0, fmt.Errorf("expected number")
	}
	return n.Float64()
}
GO_EOF

go build -o /tmp/avroencode ./src
for f in examples/*.in.json; do echo "--- $f ---"; /tmp/avroencode < "$f"; done
echo "oracle solution applied"
