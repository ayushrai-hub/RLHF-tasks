package validate

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"

	"github.com/terminus/game-replay-chronicle-normalizer/internal/format"
)

// IntegrityHash computes the chronicle integrity digest.
func IntegrityHash(events []format.EventJSON) string {
	var b strings.Builder
	for _, ev := range events {
		fmt.Fprintf(&b, "%d:%d:%d:%s;", ev.Seq, ev.Tick, ev.Type, ev.PayloadHex)
	}
	sum := sha256.Sum256([]byte(b.String()))
	return hex.EncodeToString(sum[:])
}

// MatchesIntegrity returns true when digest equals expected.
func MatchesIntegrity(events []format.EventJSON, expected string) bool {
	return IntegrityHash(events) == expected
}
