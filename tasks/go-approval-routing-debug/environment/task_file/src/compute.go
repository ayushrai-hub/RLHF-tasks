package main

// contains reports whether s is present in list.
func contains(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

// distinct returns the number of unique entries in xs.
func distinct(xs []string) int {
	seen := make(map[string]bool)
	for _, x := range xs {
		seen[x] = true
	}
	return len(seen)
}
