package spool

import "sync"

type Row struct {
	Gen uint64
	Key []byte
}

type Store struct {
	mu    sync.RWMutex
	live  map[string]uint64
	rows  map[string]map[uint64]Row
	order map[string][]uint64
}

func NewStore() *Store {
	return &Store{
		live:  make(map[string]uint64),
		rows:  make(map[string]map[uint64]Row),
		order: make(map[string][]uint64),
	}
}

func (s *Store) Install(kid string, gen uint64, key []byte) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.rows[kid] == nil {
		s.rows[kid] = make(map[uint64]Row)
	}
	s.rows[kid][gen] = Row{Gen: gen, Key: append([]byte(nil), key...)}
	s.order[kid] = append(s.order[kid], gen)
	if gen > s.live[kid] {
		s.live[kid] = gen
	}
}

func (s *Store) LiveGen(kid string) uint64 {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.live[kid]
}

func (s *Store) Rotate(kid string, gen uint64, key []byte) {
	s.Install(kid, gen, key)
}

func (s *Store) Row(kid string, gen uint64) (Row, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	m, ok := s.rows[kid]
	if !ok {
		return Row{}, false
	}
	r, ok := m[gen]
	return r, ok
}

func (s *Store) Latest(kid string) (Row, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	g := s.live[kid]
	if g == 0 {
		return Row{}, false
	}
	return s.RowLocked(kid, g)
}

func (s *Store) RowLocked(kid string, gen uint64) (Row, bool) {
	m, ok := s.rows[kid]
	if !ok {
		return Row{}, false
	}
	r, ok := m[gen]
	return r, ok
}
