# Conventions

Rules the codebase follows. The tests assume them.

## Output
- Machine-readable output goes to stdout, one record per line, space separated.
- Human error detail goes to stderr only.
- A failed command exits non-zero; a success exits zero.
- Deterministic ordering: versions ascending by precedence; `gomod` requires and
  `mvs` entries by module path ascending.

## Proxy
- Data is read live from https://proxy.golang.org; nothing is bundled.
- Raw responses are cached under /tmp/gomvs-cache so a module fetched twice is
  requested once.

## Scope
- Standard library only; keep the code gofmt-clean and vet-clean.
- docs/spec.md is authoritative for the command surface, output format and
  result tokens.
