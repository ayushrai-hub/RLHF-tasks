package chronicle

import (
	"encoding/hex"
	"encoding/json"
	"os"
	"sort"

	"github.com/terminus/game-replay-chronicle-normalizer/internal/format"
	"github.com/terminus/game-replay-chronicle-normalizer/internal/validate"
)

// Build constructs a chronicle from shard metadata and normalized events.
func Build(shards []format.ShardMeta, events []format.Event) (*format.Chronicle, error) {
	sort.Slice(shards, func(i, j int) bool {
		return shards[i].ShardID < shards[j].ShardID
	})
	outEvents := make([]format.EventJSON, 0, len(events))
	for _, ev := range events {
		outEvents = append(outEvents, format.EventJSON{
			Seq:        ev.Seq,
			Tick:       ev.Tick,
			Type:       ev.Type,
			PayloadHex: hex.EncodeToString(ev.Payload),
		})
	}
	ch := &format.Chronicle{
		Version: 1,
		Shards:  shards,
		Events:  outEvents,
	}
	ch.Integrity = validate.IntegrityHash(outEvents)
	return ch, nil
}

// WriteJSON writes chronicle to path with trailing newline.
func WriteJSON(path string, ch *format.Chronicle) error {
	data, err := json.Marshal(ch)
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(path, data, 0o644)
}

// LoadJSON reads a chronicle from disk.
func LoadJSON(path string) (*format.Chronicle, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var ch format.Chronicle
	if err := json.Unmarshal(data, &ch); err != nil {
		return nil, err
	}
	return &ch, nil
}
