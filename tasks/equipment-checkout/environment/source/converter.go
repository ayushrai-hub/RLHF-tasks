package main

import (
	"fmt"
	"strconv"
)

func parseInt64(label, s string) (int64, error) {
	n, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return 0, fmt.Errorf("invalid %s %q: must be an integer", label, s)
	}
	return n, nil
}

func formatCents(n int64) string { return fmt.Sprintf("%.2f", float64(n)) }
