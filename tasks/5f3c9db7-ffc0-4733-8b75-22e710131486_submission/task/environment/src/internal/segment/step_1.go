package segment

import (
	"hash/crc32"

	"logrecover/pkg/api"
)

func verify_frame(fr api.Frame) bool {
	if len(fr.Payload) > 65536 {
		return false
	}
	got := crc32.ChecksumIEEE(fr.Payload)
	return got == fr.CRC
}

func VerifyFrame(fr api.Frame) bool {
	return verify_frame(fr)
}
