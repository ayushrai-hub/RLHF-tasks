package segment

import (
	"encoding/hex"
	"logrecover/pkg/api"
	"logrecover/pkg/limits"
)

func FramesToEvents(frames []api.Frame) ([]api.Event, int) {
	out := make([]api.Event, 0, len(frames))
	loss := 0
	for _, fr := range frames {
		if !VerifyFrame(fr) {
			continue
		}
		ev := api.Event{
			Lamport: fr.Lamport,
			NodeID:  fr.NodeID,
			Seq:     fr.Seq,
			Payload: append([]byte(nil), fr.Payload...),
		}
		out = append(out, ev)
		if len(out) > limits.MaxEventsMerged {
			break
		}
	}
	return out, loss
}

func DecodePayloadHex(h string) ([]byte, error) {
	return hex.DecodeString(h)
}

func NormalizeFrames(frames []api.Frame) error {
	for i := range frames {
		if len(frames[i].Payload) == 0 && frames[i].PayloadHex != "" {
			b, err := hex.DecodeString(frames[i].PayloadHex)
			if err != nil {
				return err
			}
			frames[i].Payload = b
		}
	}
	return nil
}
