package relay

import "sync"

type Relay struct {
	mu sync.Mutex
	seq uint64
}

func New() *Relay {
	return &Relay{}
}

func (r *Relay) Bump() uint64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.seq++
	return r.seq
}
