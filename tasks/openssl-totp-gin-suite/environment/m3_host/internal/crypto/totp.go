package crypto

import (
	"crypto/hmac"
	"crypto/sha1"
	"encoding/binary"
	"fmt"
	"strings"
)

func PasscodeForEpoch(secret []byte, epoch int64, stepSeconds int, digits int) string {
	counter := uint64(epoch / int64(stepSeconds))
	msg := make([]byte, 8)
	binary.BigEndian.PutUint64(msg, counter)
	mac := hmac.New(sha1.New, secret)
	_, _ = mac.Write(msg)
	sum := mac.Sum(nil)
	offset := sum[len(sum)-1] & 0x0f
	code := binary.BigEndian.Uint32(sum[offset:offset+4]) & 0x7fffffff
	mod := uint32(1)
	for i := 0; i < digits; i++ {
		mod *= 10
	}
	val := code % mod
	format := fmt.Sprintf("%%0%dd", digits)
	return fmt.Sprintf(format, val)
}

func PasscodeValid(secret []byte, passcode string, epoch int64, stepSeconds, window, digits int) bool {
	passcode = strings.TrimSpace(passcode)
	for delta := -window; delta <= window; delta++ {
		stepEpoch := epoch + int64(delta*stepSeconds)
		if PasscodeForEpoch(secret, stepEpoch, stepSeconds, digits) == passcode {
			return true
		}
	}
	return false
}
