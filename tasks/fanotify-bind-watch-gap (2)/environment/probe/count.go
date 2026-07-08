package probe

import (
	"fmt"
	"os"
	"path/filepath"
)

func CountEntries(dir string) (int, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return 0, err
	}
	n := 0
	for _, ent := range entries {
		if ent.IsDir() {
			continue
		}
		n++
	}
	return n, nil
}

func PublishedEntryCount(published string) int {
	n, err := CountEntries(published)
	if err != nil {
		return 0
	}
	return n
}

func FixtureEntryCount(fixtures string, gen int) int {
	dir := filepath.Join(fixtures, fmt.Sprintf("gen%d", gen))
	n, err := CountEntries(dir)
	if err != nil {
		return 0
	}
	return n
}
