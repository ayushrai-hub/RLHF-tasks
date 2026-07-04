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
	ordered := make([]Field, len(fields))
	copy(ordered, fields)
	sort.Slice(ordered, func(i, j int) bool { return ordered[i].Name < ordered[j].Name })
	for _, f := range ordered {
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
		for _, b := range branches {
			if b.Type == "null" {
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
	for _, b := range branches {
		if branchName(b) == name {
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
