package main

// filterByStatus returns items whose status matches s.
// Used for reporting and list filtering utilities.
func filterByStatus(items []Equipment, s string) []Equipment {
	var out []Equipment
	for _, e := range items {
		if e.Status == s {
			out = append(out, e)
		}
	}
	return out
}
