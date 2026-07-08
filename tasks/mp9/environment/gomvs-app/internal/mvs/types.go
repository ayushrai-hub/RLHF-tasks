// Package mvs computes a module's dependency build list by Minimal Version
// Selection over live go.mod metadata from the module proxy.
//
// The Selected result type and the ModFetcher interface the algorithm reads
// through live here. The build-list computation itself is BuildList in build.go.
package mvs

import "gomvs/internal/modfile"

// ModFetcher supplies the parsed go.mod of one module at one exact version.
// The proxy client satisfies it.
type ModFetcher interface {
	Mod(module, version string) (*modfile.File, error)
}

// Selected is one entry of a build list: a module and the version MVS chose for
// it.
type Selected struct {
	Path    string
	Version string
}
