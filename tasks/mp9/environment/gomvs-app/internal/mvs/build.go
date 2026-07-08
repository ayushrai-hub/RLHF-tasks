package mvs

import "fmt"

// BuildList computes the Minimal Version Selection build list for a target
// module pinned at an exact version, fetching go.mod files through fetch. It
// returns the build-list entries excluding the target itself, sorted by path.
// The target's own replace and exclude directives take effect; a dependency's
// do not. See docs/spec.md for the command's output contract.
//
// STUB: returns a not_implemented error. Implement the build-list computation.
func BuildList(target, version string, fetch ModFetcher) ([]Selected, error) {
	return nil, fmt.Errorf("not_implemented")
}

// Resolve returns the selected version of dep in the build list of target at
// version, and ok=false when dep is not part of the build list.
//
// STUB: returns a not_implemented error. Implement once BuildList is written.
func Resolve(target, version, dep string, fetch ModFetcher) (string, bool, error) {
	return "", false, fmt.Errorf("not_implemented")
}
