package realm

import "sync"

type Registry struct {
	mu     sync.RWMutex
	local  string
	accept map[string]struct{}
}

func NewRegistry(local string) *Registry {
	return &Registry{local: local, accept: make(map[string]struct{})}
}

func (r *Registry) SetLocal(v string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.local = v
}

func (r *Registry) Local() string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.local
}

func (r *Registry) Allow(v string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.accept[v] = struct{}{}
}

func (r *Registry) Permits(v string) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	_, ok := r.accept[v]
	return ok
}
