package main

import (
	"fmt"
	"time"
)

const dateLayout = "2006-01-02"

// parseDate parses a YYYY-MM-DD date string.
func parseDate(s string) (time.Time, error) {
	t, err := time.Parse(dateLayout, s)
	if err != nil {
		return time.Time{}, fmt.Errorf("invalid date %q: %w", s, err)
	}
	return t, nil
}

// daysBetween returns whole days from -> to (to - from).
func daysBetween(from, to string) (int64, error) {
	t1, err := parseDate(from)
	if err != nil {
		return 0, err
	}
	t2, err := parseDate(to)
	if err != nil {
		return 0, err
	}
	return int64(t2.Sub(t1).Hours() / 24), nil
}
