package resolve

import (
	"encoding/hex"

	"example.com/gnvtlv/internal/decode"
)

type Resolved struct {
	Source       string           `json:"source"`
	Header       ResolvedHeader   `json:"header"`
	Options      []ResolvedOption `json:"options"`
	DecodeErrors []decode.Error   `json:"decode_errors"`
	Issues       []Issue          `json:"issues"`
}

type ResolvedHeader struct {
	Version          int    `json:"version"`
	OptLenWords      int    `json:"opt_len_words"`
	OptLenBytes      int    `json:"opt_len_bytes"`
	OAM              bool   `json:"oam"`
	Critical         bool   `json:"critical"`
	ProtocolType     int    `json:"protocol_type"`
	ProtocolTypeName string `json:"protocol_type_name"`
	VNI              int    `json:"vni"`
}

type ResolvedOption struct {
	Index       int         `json:"index"`
	OffsetBytes int         `json:"offset_bytes"`
	OptClass    int         `json:"opt_class"`
	Type        int         `json:"type"`
	Critical    bool        `json:"critical"`
	LengthBytes int         `json:"length_bytes"`
	Name        string      `json:"name"`
	Kind        string      `json:"kind"`
	Recognized  bool        `json:"recognized"`
	Decoded     interface{} `json:"decoded"`
	DataHex     string      `json:"data_hex"`
}

type Issue struct {
	Code     string `json:"code"`
	OptIndex int    `json:"opt_index"`
	Message  string `json:"message"`
}

func Resolve(d decode.Decoded, r *Registries) Resolved {
	out := Resolved{
		Source: d.Source,
		Header: ResolvedHeader{
			Version:      d.Header.Version,
			OptLenWords:  d.Header.OptLenWords,
			OptLenBytes:  d.Header.OptLenBytes,
			OAM:          d.Header.OAM,
			Critical:     d.Header.Critical,
			ProtocolType: d.Header.ProtocolType,
			VNI:          d.Header.VNI,
		},
		Options:      make([]ResolvedOption, 0, len(d.Options)),
		DecodeErrors: append([]decode.Error{}, d.Errors...),
		Issues:       make([]Issue, 0),
	}

	for _, raw := range d.Options {
		ro := ResolvedOption{
			Index:       raw.Index,
			OffsetBytes: raw.OffsetBytes,
			OptClass:    raw.OptClass,
			Type:        raw.Type,
			Critical:    raw.Critical,
			LengthBytes: raw.LengthBytes,
			DataHex:     raw.DataHex,
			Name:        "",
			Kind:        "unknown",
			Recognized:  false,
			Decoded:     nil,
		}
		out.Options = append(out.Options, ro)
	}
	return out
}

func decodeHexBytes(s string) []byte {
	b, err := hex.DecodeString(s)
	if err != nil {
		return nil
	}
	return b
}
