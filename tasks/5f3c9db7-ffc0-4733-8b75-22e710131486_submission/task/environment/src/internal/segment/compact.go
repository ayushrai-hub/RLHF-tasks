package segment

import "logrecover/pkg/api"

func CompactFrames(frames []api.Frame) []api.Frame {
	if len(frames) <= 1 {
		return frames
	}
	out := make([]api.Frame, 0, len(frames))
	out = append(out, frames[0])
	for i := 1; i < len(frames); i++ {
		prev := out[len(out)-1]
		cur := frames[i]
		if cur.Lamport == prev.Lamport && cur.NodeID == prev.NodeID && cur.Seq == prev.Seq {
			continue
		}
		out = append(out, cur)
	}
	return out
}
