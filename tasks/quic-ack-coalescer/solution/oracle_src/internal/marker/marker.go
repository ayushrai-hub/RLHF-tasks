package marker

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"

	"qack/internal/load"
	"qack/internal/policy"
)

// SealHex returns the 8-hex-char prefix of sha256 over the canonical preimage:
//   secret_label | kind | conn | target_low | target_high | issued_ts
// joined with the literal pipe character.
func SealHex(secret, kind, conn string, low, high, issued int64) string {
	pre := fmt.Sprintf("%s|%s|%s|%d|%d|%d", secret, kind, conn, low, high, issued)
	sum := sha256.Sum256([]byte(pre))
	return hex.EncodeToString(sum[:])[:8]
}

// Validate keeps only markers whose source is "control_plane", kind is in the
// closed enum, and whose hmac8 matches the recomputed seal. Silently drops others.
func Validate(markers []load.Marker, p *policy.Policy) []load.Marker {
	var out []load.Marker
	for _, m := range markers {
		if m.Source != "control_plane" {
			continue
		}
		if !p.IsClosedMarkerKind(m.Kind) {
			continue
		}
		want := SealHex(p.MarkerSecretLabel, m.Kind, m.Conn, m.TargetLow, m.TargetHigh, m.IssuedTs)
		if want != m.Hmac8 {
			continue
		}
		out = append(out, m)
	}
	return out
}
