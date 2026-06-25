package diag

import (
	"fmt"
	"sort"

	"terminal.local/objectmanifest/internal/store"
)

func Summarize(layout store.Layout) ([]string, error) {
	receipts, err := store.ReadReceipts(layout)
	if err != nil {
		return nil, err
	}
	tree, err := store.ScanObjectTree(layout)
	if err != nil {
		return nil, err
	}
	counts := map[string]int{}
	for _, obj := range tree {
		counts[obj.BatchID]++
	}
	lines := []string{fmt.Sprintf("objects=%d receipts=%d", len(tree), len(receipts))}
	seen := map[string]bool{}
	for _, rf := range receipts {
		r := rf.Receipt
		lines = append(lines, fmt.Sprintf("batch=%s phase=%s receipt_objects=%d files=%d", r.BatchID, r.Phase, len(r.Objects), counts[r.BatchID]))
		seen[r.BatchID] = true
	}
	extras := make([]string, 0)
	for batch := range counts {
		if !seen[batch] {
			extras = append(extras, batch)
		}
	}
	sort.Strings(extras)
	for _, batch := range extras {
		lines = append(lines, fmt.Sprintf("batch=%s phase=<missing-receipt> receipt_objects=0 files=%d", batch, counts[batch]))
	}
	return lines, nil
}
