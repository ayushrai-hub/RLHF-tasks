package vault

type SnapView struct {
	SettledPeriod int64            `json:"settled_period"`
	StagedPeriod  int64            `json:"staged_period"`
	ResumePeriod  int64            `json:"resume_period"`
	NextBindSlot  int                `json:"next_bind_slot"`
	RejectedCount int                `json:"rejected_count"`
	Committed     map[string]int64 `json:"committed_pts"`
	Pending       map[string]int64 `json:"pending_pts"`
}

func max64(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}

func clampStaged(settled int64, staged int64) int64 {
	if staged < settled {
		return settled
	}
	return staged
}

func pickResume(saved *SnapView) int64 {
	if saved == nil {
		return 0
	}
	return saved.SettledPeriod
}

func op_r(saved *SnapView, live *SnapView) *SnapView {
	out := *live
	if saved == nil {
		return &out
	}
	if saved.SettledPeriod > out.SettledPeriod {
		out.SettledPeriod = saved.SettledPeriod
	}
	if saved.StagedPeriod > out.StagedPeriod {
		out.StagedPeriod = saved.StagedPeriod
	}
	out.StagedPeriod = clampStaged(out.SettledPeriod, out.StagedPeriod)
	out.ResumePeriod = pickResume(saved)
	out.NextBindSlot = saved.NextBindSlot
	out.RejectedCount = saved.RejectedCount
	out.Committed = mergeMaps(saved.Committed, live.Committed)
	out.Pending = mergeMaps(saved.Pending, live.Pending)
	return &out
}

func mergeMaps(saved, live map[string]int64) map[string]int64 {
	out := cloneMap(live)
	for k, v := range saved {
		if cur, ok := out[k]; !ok || v > cur {
			out[k] = v
		}
	}
	return out
}

func cloneMap(src map[string]int64) map[string]int64 {
	out := make(map[string]int64, len(src))
	for k, v := range src {
		out[k] = v
	}
	return out
}

func BlendReplica(saved, live *SnapView) *SnapView {
	return op_r(saved, live)
}
