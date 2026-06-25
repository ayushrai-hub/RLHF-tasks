#!/bin/bash
set -euo pipefail
cd /app

echo "==> inspect the registry files the resolver must consult"
ls /app/configs
sed -n '1,12p' /app/configs/geneve_registry.json
sed -n '1,8p' /app/configs/ethertype_registry.json

echo "==> inspect the per-kind helpers already in place"
grep -n '^func ' /app/internal/resolve/kinds.go
grep -n '^func ' /app/internal/resolve/registry.go

echo "==> rewrite resolve.go with registry-driven Resolve"
cat > /app/internal/resolve/resolve.go <<'GOEOF'
package resolve

import (
	"encoding/hex"
	"fmt"

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
	if e, ok := r.LookupEther(d.Header.ProtocolType); ok {
		out.Header.ProtocolTypeName = e.Name
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
		entry, ok := r.LookupOption(raw.OptClass, raw.Type)
		if ok {
			ro.Recognized = true
			ro.Name = entry.Name
			ro.Kind = entry.Kind
			payload, _ := hex.DecodeString(raw.DataHex)
			if entry.FixedBytes > 0 && entry.FixedBytes != raw.LengthBytes {
				out.Issues = append(out.Issues, Issue{
					Code:     "OPT_LENGTH_MISMATCH",
					OptIndex: raw.Index,
					Message:  fmt.Sprintf("option %d kind=%s expects %d bytes, got %d", raw.Index, entry.Kind, entry.FixedBytes, raw.LengthBytes),
				})
			} else {
				switch entry.Kind {
				case "u32":
					if v, err := DecodeU32(payload); err == nil {
						ro.Decoded = v
					}
				case "u128":
					if s, err := DecodeU128(payload); err == nil {
						ro.Decoded = s
					}
				case "struct":
					if sv, err := DecodeStruct(payload); err == nil {
						ro.Decoded = sv
					}
				case "varbin":
					ro.Decoded = DecodeVarbin(payload)
				case "opaque":
					ro.Decoded = DecodeVarbin(payload)
				}
			}
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
GOEOF

echo "==> verify the rewrite landed"
grep -n 'LookupEther(d.Header.ProtocolType)' /app/internal/resolve/resolve.go
grep -n 'OPT_LENGTH_MISMATCH' /app/internal/resolve/resolve.go

if ! grep -qF 'LookupEther(d.Header.ProtocolType)' /app/internal/resolve/resolve.go; then
    echo "M2 oracle: resolve.go rewrite did not include Ethertype lookup" >&2
    exit 1
fi
if ! grep -qF 'OPT_LENGTH_MISMATCH' /app/internal/resolve/resolve.go; then
    echo "M2 oracle: resolve.go rewrite did not include OPT_LENGTH_MISMATCH" >&2
    exit 1
fi

echo "==> build and run the unit tests"
mkdir -p /app/bin
go build -o /app/bin/gnvtlv ./cmd/gnvtlv
go build ./...
go test ./internal/wire/... ./internal/decode/... ./internal/resolve/...
