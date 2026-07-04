package main

import (
	"encoding/json"
	"fmt"
)

var primitiveTypes = map[string]bool{
	"null": true, "boolean": true, "int": true, "long": true,
	"float": true, "double": true, "bytes": true, "string": true,
}

// parseSchema converts an Avro schema (already decoded from JSON) into a Schema
// tree. A schema is a type name string, a list of branches (a union), or an
// object carrying a "type" plus the members for that type.
func parseSchema(j interface{}) (*Schema, error) {
	switch t := j.(type) {
	case string:
		if primitiveTypes[t] {
			return &Schema{Type: t}, nil
		}
		return nil, fmt.Errorf("unknown type %q", t)
	case []interface{}:
		s := &Schema{Type: "union"}
		for _, b := range t {
			bs, err := parseSchema(b)
			if err != nil {
				return nil, err
			}
			s.Branches = append(s.Branches, bs)
		}
		return s, nil
	case map[string]interface{}:
		tn, _ := t["type"].(string)
		switch tn {
		case "record":
			s := &Schema{Type: "record", Name: asString(t["name"])}
			fields, _ := t["fields"].([]interface{})
			for _, f := range fields {
				fm, ok := f.(map[string]interface{})
				if !ok {
					return nil, fmt.Errorf("bad record field")
				}
				fs, err := parseSchema(fm["type"])
				if err != nil {
					return nil, err
				}
				s.Fields = append(s.Fields, Field{Name: asString(fm["name"]), Type: fs})
			}
			return s, nil
		case "enum":
			s := &Schema{Type: "enum", Name: asString(t["name"])}
			syms, _ := t["symbols"].([]interface{})
			for _, sy := range syms {
				s.Symbols = append(s.Symbols, asString(sy))
			}
			return s, nil
		case "array":
			is, err := parseSchema(t["items"])
			if err != nil {
				return nil, err
			}
			return &Schema{Type: "array", Items: is}, nil
		case "map":
			vs, err := parseSchema(t["values"])
			if err != nil {
				return nil, err
			}
			return &Schema{Type: "map", Values: vs}, nil
		case "fixed":
			sz, err := asInt(t["size"])
			if err != nil {
				return nil, err
			}
			return &Schema{Type: "fixed", Name: asString(t["name"]), Size: sz}, nil
		default:
			if primitiveTypes[tn] {
				return &Schema{Type: tn}, nil
			}
			return nil, fmt.Errorf("unknown type %q", tn)
		}
	}
	return nil, fmt.Errorf("invalid schema node")
}

func asString(v interface{}) string {
	s, _ := v.(string)
	return s
}

func asInt(v interface{}) (int, error) {
	switch n := v.(type) {
	case json.Number:
		i, err := n.Int64()
		return int(i), err
	case float64:
		return int(n), nil
	}
	return 0, fmt.Errorf("not an integer")
}
