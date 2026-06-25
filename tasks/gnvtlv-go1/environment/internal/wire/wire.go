package wire

import "encoding/binary"

const FixedHeaderLen = 8

const OptionHeaderLen = 4

type FixedHeader struct {
	Version      uint8
	OptLenWords  uint8
	OAM          bool
	Critical     bool
	Reserved6    uint8
	ProtocolType uint16
	VNI          uint32
	Reserved8    uint8
}

func ParseFixedHeader(b []byte) FixedHeader {
	_ = b[7]
	return FixedHeader{
		Version:      b[0] >> 6,
		OptLenWords:  b[0] & 0x3F,
		OAM:          (b[1] & 0x80) != 0,
		Critical:     (b[1] & 0x40) != 0,
		Reserved6:    b[1] & 0x3F,
		ProtocolType: binary.BigEndian.Uint16(b[2:4]),
		VNI:          uint32(b[4])<<16 | uint32(b[5])<<8 | uint32(b[6]),
		Reserved8:    b[7],
	}
}

type OptionHeader struct {
	OptClass   uint16
	Critical   bool
	Type7      uint8
	RBits      uint8
	LengthWord uint8
}

func ParseOptionHeader(b []byte) OptionHeader {
	_ = b[3]
	return OptionHeader{
		OptClass:   binary.BigEndian.Uint16(b[0:2]),
		Critical:   (b[2] & 0x80) != 0,
		Type7:      b[2] & 0x7F,
		RBits:      b[3] & 0x07,
		LengthWord: (b[3] >> 3) & 0x1F,
	}
}

func (o OptionHeader) TypeByte() uint8 {
	var c uint8
	if o.Critical {
		c = 0x80
	}
	return c | (o.Type7 & 0x7F)
}
