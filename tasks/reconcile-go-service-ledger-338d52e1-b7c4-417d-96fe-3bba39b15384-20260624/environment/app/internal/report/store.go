package report

import (
	"sync"

	"service-ledger/internal/summary"
)

type Store struct {
	mu      sync.Mutex
	reports map[string]summary.Report
}

func NewStore() *Store {
	return &Store{reports: map[string]summary.Report{}}
}

func (s *Store) Put(rep summary.Report) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	id := ID(rep)
	s.reports[id] = rep
	return id
}

func (s *Store) Get(id string) (summary.Report, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	rep, ok := s.reports[id]
	return rep, ok
}
