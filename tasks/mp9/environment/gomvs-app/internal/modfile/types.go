// Package modfile parses the subset of the go.mod grammar the resolver needs:
// the module directive, the go directive, the require directives in both their
// single-line and parenthesised block forms, and the replace and exclude
// directives (also in both forms). The parser tolerates the older go.mod
// dialect that quotes paths and versions, and it records which requirements are
// marked // indirect.
//
// The File, Require, Replace and Exclude types live here. The parser itself is
// Parse in parse.go.
package modfile

// Require is one require directive: the required module path, its version, and
// whether the line carried an // indirect marker.
type Require struct {
	Path     string
	Version  string
	Indirect bool
}

// Replace is one replace directive. OldPath is the module being replaced and
// OldVersion is the specific version it targets, or the empty string for a
// wildcard replacement of every version of OldPath. NewPath and NewVersion name
// the replacement module and version.
type Replace struct {
	OldPath    string
	OldVersion string
	NewPath    string
	NewVersion string
}

// Exclude is one exclude directive: an exact module path and version the main
// module removes from consideration.
type Exclude struct {
	Path    string
	Version string
}

// File is a parsed go.mod. Path is the module's own path from the module
// directive. Go is the version from the go directive, or the empty string when
// the file has none. Requires holds every require directive in file order.
// Replaces and Excludes hold the replace and exclude directives in file order.
type File struct {
	Path     string
	Go       string
	Requires []Require
	Replaces []Replace
	Excludes []Exclude
}
