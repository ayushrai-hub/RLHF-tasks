# Ninja depfile layout for depfix

Normalized dependency manifests live under `/app/build/deps/` as `<target>.dep`.

## Path rules

- Each data line is a project-relative path such as `include/depfix/config.hpp` (never an absolute `/app/...` path inside the file).
- Paths must reference the live tree under `include/depfix/` (not legacy `include/depfix/old/`).

## Per-target header closure

Each depfix target registers one or more `.cpp` translation units when depfiles are enabled. A header **participates** in a target when it is reachable by recursively following quoted `#include "depfix/..."` lines starting from that target's registered sources only (do not scan unrelated targets' sources).

Reachability includes headers under `include/depfix/`, `include/depfix/detail/`, and `include/depfix/generated/`. System-style includes (`#include <...>`) are ignored.

## Line ordering

After the optional `# depfix normalized deps for <target>` comment line, every data line must be sorted in ascending lexicographic order.

## Manifest footer

Each `.dep` file ends with two comment lines derived from the **sorted** data lines only (exclude the header comment and footer comments):

- `# depfix-lines=<N>` where `<N>` is the number of data lines.
- `# depfix-digest=<hex>` where `<hex>` is the lowercase SHA-256 digest of the UTF-8 string formed by joining the **sorted** data lines with `\n` plus a trailing `\n`. The digest must be computed after sorting; using pre-sort or glob order is invalid.

## Stale overlay

Live manifests under `/app/build/deps/` must not be overwritten from `/app/build/deps-stale/` during builds. POST_BUILD steps must not copy `/app/build/deps-stale/` into `/app/build/deps/`. After repair, `/app/build/deps-stale/` must be absent or contain no `.dep` files.

## Targets and registered sources

| Target | Registered sources |
|--------|-------------------|
| `depfix_hash` | `src/detail/hash_mix.cpp` |
| `depfix_core` | `src/core.cpp` |
| `depfix_util` | `src/util.cpp` |
| `depfix_app` | `src/main.cpp` |

The build audit CLI reads `/app/build/.ninja_log` after a touch sequence and writes JSON reports under paths supplied at runtime.
