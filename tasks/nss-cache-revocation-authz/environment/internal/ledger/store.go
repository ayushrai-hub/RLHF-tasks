package ledger

import (
	"path/filepath"
	"sort"

	"localauthz/internal/model"
)

type Store struct {
	entries map[string]model.CacheEntry
}

func NewStore() *Store {
	return &Store{entries: map[string]model.CacheEntry{}}
}

func NewStoreFromEntries(entries []model.CacheEntry) *Store {
	s := NewStore()
	for _, entry := range entries {
		s.Upsert(entry)
	}
	return s
}

func (s *Store) Upsert(entry model.CacheEntry) {
	s.entries[entry.Username] = entry
}

func (s *Store) MarkMissingAsRevoked(current map[string]bool, revision int, proof model.Proof, tick int, bound int, proofAge int, refreshEpoch int) {
	for username, entry := range s.entries {
		if current[username] {
			continue
		}
		entry.Groups = []string{}
		entry.DirectoryRevision = revision
		entry.ProofRevision = proof.Revision
		entry.ProofAge = proofAge
		entry.RefreshedAt = tick
		entry.ExpiresAt = tick + bound
		entry.RefreshEpoch = refreshEpoch
		entry.Revoked = true
		s.entries[username] = entry
	}
}

func (s *Store) Get(username string) (model.CacheEntry, bool) {
	entry, ok := s.entries[username]
	return entry, ok
}

func (s *Store) Entries() []model.CacheEntry {
	out := make([]model.CacheEntry, 0, len(s.entries))
	for _, entry := range s.entries {
		entry.Groups = append([]string(nil), entry.Groups...)
		sort.Strings(entry.Groups)
		out = append(out, entry)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Username < out[j].Username })
	return out
}

func LoadStore(dir string) (*Store, error) {
	path := filepath.Join(dir, "cache_entries.json")
	entries, err := LoadEntries(path)
	if err != nil {
		return nil, err
	}
	return NewStoreFromEntries(entries), nil
}
