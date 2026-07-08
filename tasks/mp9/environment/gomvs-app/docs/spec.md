# gomvs CLI specification

Command and protocol reference for the `gomvs` tool. Build it with
`go build -o /app/gomvs .` from the module root using the Go standard library
only. Every command reads live from the public Go module proxy at
`https://proxy.golang.org`; nothing is bundled and the tool cannot run offline.
Raw proxy responses are cached under `/tmp/gomvs-cache`.

All machine-readable output is written to stdout, one record per line, space
separated. Stderr is reserved for human debugging. A failing command exits
non-zero.

## Proxy access

Data comes from the standard Go module proxy endpoints for a module path P and
version V:

- `GET /<P>/@v/list` - the plain-text list of tagged versions.
- `GET /<P>/@v/<V>.info` - JSON metadata for one version.
- `GET /<P>/@v/<V>.mod` - the raw `go.mod` for that version.

Module paths and versions are case-encoded the way the proxy requires before a
request is made, so a module whose path contains uppercase letters still
resolves.

## Commands

### versions
`versions <module>`. Prints every version the proxy lists for the module, one
per line, in ascending Go-module version precedence order. Exits zero.

### gomod
`gomod <module> <version>`. Fetches and parses that version's go.mod and prints,
in this order:

```
module <path>
go <goversion>
require <path> <version>
exclude <path> <version>
replace <oldpath> [<oldversion>] => <newpath> <newversion>
```

The `go` line prints the declared language version, or `go none` when the file
declares none. Then the `require` lines, one per require directive, sorted by
module path ascending, each version echoed exactly as written. Then any
`exclude` lines, sorted by path then version. Then any `replace` lines, sorted by
old path then old version; the old-version field is printed only when the
directive pinned one. The parser accepts the go.mod grammar as it appears on the
proxy: `module`, `go`, `require`, `exclude` and `replace` directives in both the
single-line and parenthesised block forms, the older dialect that double-quotes
paths and versions, `// indirect` markers and `//` comments, and the `=>` replace
arrow with an optional left-hand version. Exits zero.

### mvs
`mvs <module> <version>`. Prints the Minimal Version Selection build list of the
target at the given version over the live go.mod graph: one
`<module> <selected-version>` line per module, sorted by module path ascending,
excluding the target module itself. The target is the main module, always at its
pinned version and never an entry of its own build list. The target's own
`replace` and `exclude` directives take effect; directives found in a
dependency's go.mod are read but not applied. Exits zero.

### resolve
`resolve <module> <version> <dep>`. Prints the version selected for module `dep`
in the target's build list and exits zero. When `dep` is not part of the build
list, prints `not_found` and exits non-zero.

## Errors

A proxy request for a module or version that does not exist, a malformed version
in a list, or a go.mod that cannot be parsed is a failure: a human-readable
message goes to stderr and the tool exits non-zero. Machine-readable result
tokens such as `not_found` go to stdout.
