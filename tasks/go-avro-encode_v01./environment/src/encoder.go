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
		writeBytes(buf, data)
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
