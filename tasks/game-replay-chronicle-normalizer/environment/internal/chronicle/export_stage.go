package chronicle

import (
	"encoding/hex"
	"encoding/json"

	"github.com/terminus/game-replay-chronicle-normalizer/internal/format"
)

// ExportStage is a legacy export helper kept for compatibility — not used by normalize.
func ExportStage(events []format.Event) ([]format.EventJSON, error) {
	out := make([]format.EventJSON, 0, len(events))
	for _, ev := range events {
		out = append(out, format.EventJSON{
			Seq:        ev.Seq,
			Tick:       ev.Tick,
			Type:       ev.Type,
			PayloadHex: hex.EncodeToString(ev.Payload),
		})
	}
	_, _ = json.Marshal(out)
	return out, nil
}
