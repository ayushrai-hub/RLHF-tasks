# gomvs

A command-line tool that queries the public Go module proxy and resolves a
module's dependency versions by Minimal Version Selection. Given a module path
and an exact version, `gomvs` lists published versions, prints a parsed `go.mod`,
computes the MVS build list over the live dependency graph, and reports the
version chosen for a given dependency.

## Build

    go build -o /app/gomvs .

Standard library only; no third-party modules.

## Layout

- `main.go` - entrypoint, delegates to the cli package.
- `internal/proxy` - read-only Go module proxy client and path escaping.
- `internal/semver` - version parsing and precedence ordering.
- `internal/modfile` - the go.mod parser.
- `internal/mvs` - the Minimal Version Selection build list.
- `internal/cli` - subcommand wiring and output formatting.
- `docs/spec.md` - the authoritative command and protocol reference.

## Usage

    gomvs versions rsc.io/sampler
    gomvs gomod rsc.io/quote v1.5.2
    gomvs mvs rsc.io/quote v1.5.2
    gomvs resolve rsc.io/quote v1.5.2 rsc.io/sampler

Every command reads live from https://proxy.golang.org; the tool cannot run
offline. See `docs/spec.md` for the full surface and output formats.
