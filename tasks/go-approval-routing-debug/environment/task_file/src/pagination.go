package main

import (
	"net/http"
	"strconv"
)

// clamp bounds x to the inclusive range [0, n].
func clamp(x, n int) int {
	if x < 0 {
		return 0
	}
	if x > n {
		return n
	}
	return x
}

// parsePaging reads 1-based page and limit query parameters with defaults
// page=1 and limit=20.
func parsePaging(r *http.Request) (page, limit int) {
	page, limit = 1, 20
	if p := r.URL.Query().Get("page"); p != "" {
		if v, err := strconv.Atoi(p); err == nil && v > 0 {
			page = v
		}
	}
	if l := r.URL.Query().Get("limit"); l != "" {
		if v, err := strconv.Atoi(l); err == nil && v > 0 {
			limit = v
		}
	}
	return page, limit
}
