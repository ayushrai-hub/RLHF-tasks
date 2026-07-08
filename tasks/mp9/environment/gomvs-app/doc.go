// Command gomvs queries the live Go module proxy and resolves a module's
// dependency versions by Minimal Version Selection.
//
// Given a module path and an exact version, gomvs lists a module's published
// versions, prints the parsed contents of a version's go.mod, computes the MVS
// build list over the transitive go.mod graph, and reports the version selected
// for a particular dependency. Everything is read live from
// https://proxy.golang.org over the network; nothing is bundled.
//
// The command surface is:
//
//	gomvs versions <module>
//	gomvs gomod <module> <version>
//	gomvs mvs <module> <version>
//	gomvs resolve <module> <version> <dep>
//
// See docs/spec.md for the proxy protocol, the version precedence rules, the
// go.mod grammar and the exact output format of every command.
package main
