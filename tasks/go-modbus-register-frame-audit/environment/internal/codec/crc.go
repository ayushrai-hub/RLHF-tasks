package codec

import "hash/crc32"

func FrameChecksum(data []byte) uint16 {
	return uint16(crc32.ChecksumIEEE(data) & 0xFFFF)
}
