package decode

import (
	"fmt"

	"example.com/gnvtlv/internal/wire"
)

type Decoded struct {
	Source     string      `json:"source"`
	Header     Header      `json:"header"`
	Options    []RawOption `json:"options"`
	OuterBytes int         `json:"outer_bytes"`
	InnerBytes int         `json:"inner_bytes"`
	Errors     []Error     `json:"errors"`
}

type Header struct {
	Version      int  `json:"version"`
	OptLenWords  int  `json:"opt_len_words"`
	OptLenBytes  int  `json:"opt_len_bytes"`
	OAM          bool `json:"oam"`
	Critical     bool `json:"critical"`
	Reserved6    int  `json:"reserved6"`
	ProtocolType int  `json:"protocol_type"`
	VNI          int  `json:"vni"`
	Reserved8    int  `json:"reserved8"`
}

type RawOption struct {
	Index       int    `json:"index"`
	OffsetBytes int    `json:"offset_bytes"`
	OptClass    int    `json:"opt_class"`
	Type        int    `json:"type"`
	Critical    bool   `json:"critical"`
	RBits       int    `json:"r_bits"`
	LengthWords int    `json:"length_words"`
	LengthBytes int    `json:"length_bytes"`
	DataHex     string `json:"data_hex"`
}

type Error struct {
	Code     string `json:"code"`
	Where    string `json:"where"`
	Message  string `json:"message"`
	OptIndex int    `json:"opt_index"`
}

func Decode(source string, data []byte) (Decoded, error) {
	d := Decoded{Source: source, OuterBytes: len(data), Options: []RawOption{}, Errors: []Error{}}

	if len(data) < wire.FixedHeaderLen {
		return d, fmt.Errorf("short packet: have %d bytes, need >= %d", len(data), wire.FixedHeaderLen)
	}

	fh := wire.ParseFixedHeader(data[:wire.FixedHeaderLen])
	d.Header = Header{
		Version:      int(fh.Version),
		OptLenWords:  int(fh.OptLenWords),
		OptLenBytes:  int(fh.OptLenWords) * 4,
		OAM:          fh.OAM,
		Critical:     fh.Critical,
		Reserved6:    int(fh.Reserved6),
		ProtocolType: int(fh.ProtocolType),
		VNI:          int(fh.VNI),
		Reserved8:    int(fh.Reserved8),
	}

	if fh.Version != 0 {
		d.Errors = append(d.Errors, Error{
			Code: "VERSION_NONZERO", Where: "header",
			Message:  fmt.Sprintf("Version=%d, expected 0", fh.Version),
			OptIndex: -1,
		})
	}
	if fh.Reserved6 != 0 {
		d.Errors = append(d.Errors, Error{
			Code: "RESERVED6_NONZERO", Where: "header",
			Message:  fmt.Sprintf("Rsvd=%d, expected 0", fh.Reserved6),
			OptIndex: -1,
		})
	}
	if fh.Reserved8 != 0 {
		d.Errors = append(d.Errors, Error{
			Code: "RESERVED8_NONZERO", Where: "header",
			Message:  fmt.Sprintf("trailing reserved=%d, expected 0", fh.Reserved8),
			OptIndex: -1,
		})
	}

	optBytes := int(fh.OptLenWords) * 4
	tail := data[wire.FixedHeaderLen:]
	if len(tail) < optBytes {
		d.Errors = append(d.Errors, Error{
			Code: "OPT_LEN_OVERRUN", Where: "header",
			Message: fmt.Sprintf("OptLen=%d words (%d bytes), only %d bytes available",
				fh.OptLenWords, optBytes, len(tail)),
			OptIndex: -1,
		})
		return d, nil
	}

	optArea := tail[:optBytes]
	innerStart := wire.FixedHeaderLen + optBytes
	d.InnerBytes = len(data) - innerStart

	idx := 0
	pos := 0
	for pos < len(optArea) {
		if len(optArea)-pos < wire.OptionHeaderLen {
			d.Errors = append(d.Errors, Error{
				Code: "OPT_AREA_ALIGN", Where: "options",
				Message: fmt.Sprintf("option area misaligned at option %d: %d trailing bytes",
					idx, len(optArea)-pos),
				OptIndex: idx,
			})
			return d, nil
		}
		oh := wire.ParseOptionHeader(optArea[pos : pos+wire.OptionHeaderLen])
		payloadBytes := int(oh.LengthWord) * 4
		if pos+wire.OptionHeaderLen+payloadBytes > len(optArea) {
			d.Errors = append(d.Errors, Error{
				Code: "OPT_PAYLOAD_OVERRUN", Where: "options",
				Message: fmt.Sprintf("option %d declares %d-byte payload, only %d bytes remain",
					idx, payloadBytes, len(optArea)-pos-wire.OptionHeaderLen),
				OptIndex: idx,
			})
			return d, nil
		}
		payload := optArea[pos+wire.OptionHeaderLen : pos+wire.OptionHeaderLen+payloadBytes]
		d.Options = append(d.Options, RawOption{
			Index:       idx,
			OffsetBytes: wire.FixedHeaderLen + pos,
			OptClass:    int(oh.OptClass),
			Type:        int(oh.Type7),
			Critical:    oh.Critical,
			RBits:       int(oh.RBits),
			LengthWords: int(oh.LengthWord),
			LengthBytes: payloadBytes,
			DataHex:     Hex(payload),
		})
		pos += wire.OptionHeaderLen + payloadBytes
		idx++
	}
	return d, nil
}

const hexdigits = "0123456789abcdef"

func Hex(b []byte) string {
	out := make([]byte, len(b)*2)
	for i, v := range b {
		out[i*2] = hexdigits[v>>4]
		out[i*2+1] = hexdigits[v&0x0F]
	}
	return string(out)
}
