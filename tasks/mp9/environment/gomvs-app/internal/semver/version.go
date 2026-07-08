// Package semver parses and orders the version strings used by the Go module
// system: canonical MAJOR.MINOR.PATCH tags, optional pre-release and build
// metadata, the +incompatible marker on unmigrated v2+ modules, and the
// timestamp-and-hash pseudo-versions the proxy mints for untagged commits.
//
// The Version type and its string parser live here. The precedence ordering
// (Compare and Sort) lives in order.go, because ordering pre-release and
// pseudo-version identifiers correctly is the part that a naive lexical sort
// gets wrong.
package semver

import (
	"fmt"
	"strconv"
	"strings"
)

// Version is a parsed Go module version. Raw preserves the exact input string
// so callers can echo the original tag back unchanged.
type Version struct {
	Major int
	Minor int
	Patch int
	Pre   string // pre-release identifiers after '-', without the leading '-'
	Build string // build metadata after '+', without the leading '+'
	Raw   string
}

// Parse reads a version string such as "v1.5.2", "v0.9.9-pre1",
// "v2.0.0+incompatible" or a pseudo-version like
// "v0.0.0-20170915032832-14c0d48ead0c" into a Version. A leading "v" is
// required by the module system and is accepted here; the numeric core must
// have three dot-separated components.
func Parse(s string) (Version, error) {
	raw := s
	s = strings.TrimSpace(s)
	if s == "" {
		return Version{}, fmt.Errorf("empty version")
	}
	if !strings.HasPrefix(s, "v") {
		return Version{}, fmt.Errorf("version %q must start with v", raw)
	}
	body := s[1:]

	var build string
	if i := strings.IndexByte(body, '+'); i >= 0 {
		build = body[i+1:]
		body = body[:i]
	}
	var pre string
	if i := strings.IndexByte(body, '-'); i >= 0 {
		pre = body[i+1:]
		body = body[:i]
	}

	parts := strings.Split(body, ".")
	if len(parts) != 3 {
		return Version{}, fmt.Errorf("version %q must have three numeric components", raw)
	}
	nums := make([]int, 3)
	for i, p := range parts {
		n, err := strconv.Atoi(p)
		if err != nil || n < 0 {
			return Version{}, fmt.Errorf("bad numeric component in %q", raw)
		}
		nums[i] = n
	}
	return Version{
		Major: nums[0],
		Minor: nums[1],
		Patch: nums[2],
		Pre:   pre,
		Build: build,
		Raw:   raw,
	}, nil
}

// String returns the original input the version was parsed from.
func (v Version) String() string { return v.Raw }
