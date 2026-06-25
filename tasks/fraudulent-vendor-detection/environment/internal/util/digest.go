package util

import (
	"crypto/sha256"
	"fmt"
	"strings"
)

func Digest(parts ...string) string {
	h := sha256.New()
	h.Write([]byte(strings.Join(parts, "|")))
	return fmt.Sprintf("%x", h.Sum(nil))
}
