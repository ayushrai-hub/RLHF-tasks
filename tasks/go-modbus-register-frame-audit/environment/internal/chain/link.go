package chain

import (
	"crypto/sha256"
	"fmt"

	"example.com/registeraudit/internal/codec"
)

func Root(frames []codec.Frame) (string, error) {
	prev := "0000000000000000000000000000000000000000000000000000000000000000"
	for _, fr := range frames {
		raw, err := codec.CanonicalBody(fr)
		if err != nil {
			continue
		}
		h := sha256.Sum256(append(append([]byte(prev), ':'), raw...))
		prev = fmt.Sprintf("%x", h)
	}
	return prev, nil
}
