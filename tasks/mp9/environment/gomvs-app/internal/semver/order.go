package semver

// Compare orders two versions by Go module precedence and returns -1, 0 or 1.
// See docs/spec.md for the precedence rules over the numeric core, pre-release
// identifiers and build metadata.
//
// STUB: treats every pair as equal. Implement the precedence ordering.
func Compare(a, b Version) int {
	return 0
}

// Sort orders a slice of versions ascending in place by module precedence.
//
// STUB: leaves the slice untouched. Implement once Compare is written.
func Sort(vs []Version) {
}

// Max returns the greater of two versions by precedence.
//
// STUB: returns the first argument. Implement once Compare is written.
func Max(a, b Version) Version {
	return a
}
