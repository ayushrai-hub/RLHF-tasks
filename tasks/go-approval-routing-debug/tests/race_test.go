package main

import (
	"sync"
	"testing"
)

// TestRaceGetUpdate drives the read path (Get) concurrently with the write path
// (Update) on a shared set of change requests. A correct service hands callers
// detached snapshots and never mutates state a reader can still observe, so this
// test must pass cleanly under `go test -race`. An implementation that returns
// aliases of internal/cached state, or mutates a cached view in place, trips the
// race detector here regardless of where the underlying bug lives.
func TestRaceGetUpdate(t *testing.T) {
	svc := NewService()

	var ids []string
	for i := 0; i < 6; i++ {
		v, err := svc.Create(CreateRequest{
			Title:  "t",
			Author: "a",
			Stages: []Stage{{Name: "s", Required: 1, Eligible: []string{"a", "b"}}},
		})
		if err != nil {
			t.Fatalf("create: %v", err)
		}
		ids = append(ids, v.ID)
	}

	var wg sync.WaitGroup
	stop := make(chan struct{})

	// Readers: continuously read fields off the returned views.
	for r := 0; r < 6; r++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			sink := 0
			for {
				select {
				case <-stop:
					_ = sink
					return
				default:
				}
				for _, id := range ids {
					if v, err := svc.Get(id); err == nil {
						sink += v.Version + len(v.Title) + len(v.Approvals)
					}
				}
			}
		}()
	}

	// A single writer per request keeps the If-Match version in sync, so every
	// Update succeeds and mutates state.
	ver := make(map[string]int, len(ids))
	for _, id := range ids {
		ver[id] = 1
	}
	wg.Add(1)
	go func() {
		defer wg.Done()
		title := "edited"
		for k := 0; k < 4000; k++ {
			for _, id := range ids {
				if _, err := svc.Update(id, ChangeRequestUpdate{Title: &title}, ver[id]); err == nil {
					ver[id]++
				}
			}
		}
		close(stop)
	}()

	wg.Wait()
}
