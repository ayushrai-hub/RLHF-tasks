package main

import (
	"encoding/json"
	"fmt"
	"strconv"
)

// Sequence encoding and decoding. DO NOT MODIFY this file.
//
// A Seq is encoded as compact JSON:
//   {"finite":true,"lits":[{"b":[104,105],"exact":true}, ...]}   (finite)
//   {"finite":false}                                             (infinite)
// where each literal's "b" is its bytes as an array of 0..255 integers.

type jsonLit struct {
	B     []int `json:"b"`
	Exact bool  `json:"exact"`
}
type jsonSeq struct {
	Finite bool       `json:"finite"`
	Lits   *[]jsonLit `json:"lits,omitempty"`
}

// ParseSeq decodes one Seq from its JSON encoding. Building a Seq normalizes it:
// a literal that is identical (same bytes AND same exact flag) to the literal
// immediately before it is dropped, since it can never contribute anything new.
func ParseSeq(spec string) (Seq, error) {
	var js jsonSeq
	if err := json.Unmarshal([]byte(spec), &js); err != nil {
		return Seq{}, fmt.Errorf("bad seq spec: %v", err)
	}
	if !js.Finite {
		return Seq{Finite: false}, nil
	}
	s := Seq{Finite: true, Lits: []Literal{}}
	if js.Lits != nil {
		for _, l := range *js.Lits {
			b := make([]byte, len(l.B))
			for i, v := range l.B {
				b[i] = byte(v)
			}
			lit := Literal{Bytes: b, Exact: l.Exact}
			if n := len(s.Lits); n > 0 && s.Lits[n-1].Exact == lit.Exact && bytesEqual(s.Lits[n-1].Bytes, lit.Bytes) {
				continue
			}
			s.Lits = append(s.Lits, lit)
		}
	}
	return s, nil
}

// DumpSeq encodes a Seq back to the compact JSON form above.
func DumpSeq(s *Seq) string {
	if !s.Finite {
		return `{"finite":false}`
	}
	b := make([]byte, 0, 64)
	b = append(b, `{"finite":true,"lits":[`...)
	for i := range s.Lits {
		if i > 0 {
			b = append(b, ',')
		}
		b = append(b, `{"b":[`...)
		for j, by := range s.Lits[i].Bytes {
			if j > 0 {
				b = append(b, ',')
			}
			b = strconv.AppendInt(b, int64(by), 10)
		}
		b = append(b, `],"exact":`...)
		if s.Lits[i].Exact {
			b = append(b, "true"...)
		} else {
			b = append(b, "false"...)
		}
		b = append(b, '}')
	}
	b = append(b, `]}`...)
	return string(b)
}
