package ingest

import (
	"vendorlab/internal/sim"
	"vendorlab/batch"
)

func (s *State) flushAccount(account string, mode string) {
	s.Committed[account] = batch.Op_c(s.Committed[account], s.Pending[account], mode)
	s.Pending[account] = 0
}

func (s *State) flushAll(accounts []sim.LimitRow, mode string) {
	for _, t := range accounts {
		s.flushAccount(t.AccountID, mode)
	}
}
