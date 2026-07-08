package directory

import (
	"encoding/json"
	"fmt"
	"os"

	"localauthz/internal/model"
)

type Book struct {
	Scenario model.Scenario
	byRev    map[int]model.DirectorySnapshot
}

func LoadScenario(path string) (*Book, []byte, error) {
	payload, err := os.ReadFile(path)
	if err != nil {
		return nil, nil, err
	}
	var scenario model.Scenario
	if err := json.Unmarshal(payload, &scenario); err != nil {
		return nil, nil, fmt.Errorf("parse scenario: %w", err)
	}
	book := &Book{Scenario: scenario, byRev: map[int]model.DirectorySnapshot{}}
	for _, snap := range scenario.Snapshots {
		book.byRev[snap.Revision] = NormalizeSnapshot(snap)
	}
	return book, payload, nil
}

func (b *Book) Snapshot(revision int) (model.DirectorySnapshot, bool) {
	snap, ok := b.byRev[revision]
	return snap, ok
}
