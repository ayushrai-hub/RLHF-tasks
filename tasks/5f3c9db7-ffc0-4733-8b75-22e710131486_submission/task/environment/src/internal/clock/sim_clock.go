package clock

type Sim struct {
	ms int64
}

func New() *Sim { return &Sim{} }

func (s *Sim) AdvanceMS(n int) { s.ms += int64(n) }

func (s *Sim) NowMS() int { return int(s.ms) }
