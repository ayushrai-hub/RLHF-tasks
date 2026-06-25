package resolve

import (
	"encoding/binary"
	"fmt"
)

func DecodeU32(payload []byte) (uint32, error) {
	if len(payload) != 4 {
		return 0, fmt.Errorf("u32 kind: payload len=%d, expected 4", len(payload))
	}
	return binary.BigEndian.Uint32(payload), nil
}

func DecodeU128(payload []byte) (string, error) {
	if len(payload) != 16 {
		return "", fmt.Errorf("u128 kind: payload len=%d, expected 16", len(payload))
	}
	return hexOf(payload), nil
}

func DecodeVarbin(payload []byte) string {
	return hexOf(payload)
}

type StructValue struct {
	Tag  uint32 `json:"tag"`
	Tail string `json:"tail_hex"`
}

func DecodeStruct(payload []byte) (StructValue, error) {
	if len(payload) < 4 {
		return StructValue{}, fmt.Errorf("struct kind: payload len=%d, need >= 4", len(payload))
	}
	return StructValue{
		Tag:  binary.BigEndian.Uint32(payload[:4]),
		Tail: hexOf(payload[4:]),
	}, nil
}

const hexAlphabet = "0123456789abcdef"

func hexOf(b []byte) string {
	out := make([]byte, len(b)*2)
	for i, v := range b {
		out[i*2] = hexAlphabet[v>>4]
		out[i*2+1] = hexAlphabet[v&0x0F]
	}
	return string(out)
}
