package alias

import "sync"

type MapStore struct {
	mu    sync.RWMutex
	gen   uint64
	table map[string]string
	cache map[string]string
}

func NewMapStore() *MapStore {
	return &MapStore{
		table: make(map[string]string),
		cache: make(map[string]string),
	}
}

func (m *MapStore) Generation() uint64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.gen
}

func (m *MapStore) Upsert(ext, principal string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.table[ext] = principal
}

func (m *MapStore) Reload(mapping map[string]string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.gen++
	m.table = make(map[string]string, len(mapping))
	for k, v := range mapping {
		m.table[k] = v
	}
	m.cache = make(map[string]string)
}

func (m *MapStore) Snapshot() map[string]string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make(map[string]string, len(m.table))
	for k, v := range m.table {
		out[k] = v
	}
	return out
}
