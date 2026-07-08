package edi

import "strings"

type Segment struct {
	ID     string
	Fields []string
	Raw    string
}

func SplitSegments(raw string) []string {
	chunks := strings.FieldsFunc(raw, func(r rune) bool {
		return r == '~' || r == '\n' || r == '\r'
	})
	out := make([]string, 0, len(chunks))
	for _, chunk := range chunks {
		if strings.TrimSpace(chunk) == "" {
			continue
		}
		out = append(out, chunk)
	}
	return out
}

func ParseSegment(raw string, elemSep byte) Segment {
	sep := string([]byte{elemSep})
	fields := strings.Split(raw, sep)
	id := ""
	if len(fields) > 0 {
		id = fields[0]
	}
	return Segment{ID: id, Fields: fields, Raw: raw}
}
