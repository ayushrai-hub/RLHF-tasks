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

func pickResume(saved *SnapView) int64 {
	if saved == nil {
		return 0
	}
	base := saved.SettledPeriod + 1
	if saved.StagedPeriod > saved.SettledPeriod {
		return base
	}
	return base
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
	out.ResumePeriod = pickResume(saved)
	if saved.StagedPeriod > saved.SettledPeriod {
		out.ResumePeriod = max64(out.ResumePeriod, saved.SettledPeriod+1)
	}
	out.NextBindSlot = saved.NextBindSlot
	out.RejectedCount = saved.RejectedCount
	out.Committed = cloneMap(saved.Committed)
	out.Pending = cloneMap(saved.Pending)
	return &out
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
