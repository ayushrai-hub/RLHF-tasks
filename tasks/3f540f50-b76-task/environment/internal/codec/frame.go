package codec

import (
	"encoding/binary"
	"errors"
	"fmt"
)

var (
	ErrShortFrame = errors.New("mreg frame truncated")
	ErrBadMagic   = errors.New("mreg magic mismatch")
)

const (
	HeaderLen = 18
	Magic     = "MREG"
)

type Frame struct {
	Segment  uint8
	Profile  uint8
	Slave    uint8
	Func     uint8
	Reg      uint16
	Count    uint16
	Seq      uint32
	Payload  []byte
}

func ParseFrames(blob []byte) ([]Frame, int, error) {
	off := 0
	var out []Frame
	crcFails := 0
	for off < len(blob) {
		if len(blob)-off < HeaderLen+2 {
			return nil, crcFails, ErrShortFrame
		}
		if string(blob[off:off+4]) != Magic {
			return nil, crcFails, ErrBadMagic
		}
		segment := blob[off+4]
		profile := blob[off+5]
		slave := blob[off+6]
		funcCode := blob[off+7]
		reg := binary.BigEndian.Uint16(blob[off+8:])
		count := binary.BigEndian.Uint16(blob[off+10:])
		seq := binary.BigEndian.Uint32(blob[off+12:])
		plen := binary.BigEndian.Uint16(blob[off+16:])
		end := off + HeaderLen + int(plen)
		if end+2 > len(blob) {
			return nil, crcFails, ErrShortFrame
		}
		body := blob[off:end]
		want := binary.LittleEndian.Uint16(blob[end : end+2])
		got := FrameChecksum(body)
		if got != want {
			crcFails++
			off = end + 2
			continue
		}
		payload := append([]byte(nil), blob[off+HeaderLen:end]...)
		out = append(out, Frame{
			Segment: segment,
			Profile: profile,
			Slave:   slave,
			Func:    funcCode,
			Reg:     reg,
			Count:   count,
			Seq:     seq,
			Payload: payload,
		})
		off = end + 2
	}
	return out, crcFails, nil
}

func CanonicalBody(fr Frame) ([]byte, error) {
	if fr.Func >= 0x80 {
		return nil, fmt.Errorf("exception frame not chained")
	}
	if fr.Func == 0x00 {
		return nil, fmt.Errorf("checkpoint not chained")
	}
	return append([]byte(nil), fr.Payload...), nil
}
