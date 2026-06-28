package codec

import (
	"crypto/sha256"
	"encoding/hex"
	"logrecover/pkg/api"
)

func CanonicalDigestHex(events []api.Event) string {
	h := sha256.New()
	for _, ev := range events {
		h.Write(api.CanonicalRecordBytes(ev))
	}
	return hex.EncodeToString(h.Sum(nil))
}
