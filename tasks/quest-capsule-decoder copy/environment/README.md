# qcap — QuestCapsule loader

A small PHP library and CLI for reading QuestCapsule games. A capsule is a tiny JSON spec
plus rows in a shared SQLite cartridge; this tool decodes a capsule's header, rebuilds its
room graph, and plays its save states to completion.

## Layout

- `bin/qcap.php` — CLI entry point (`decode`, `graph`, `solve`).
- `src/QuestCapsule/` — the library: glyph handling, header parsing, cartridge access,
  graph reconstruction, and the run solver.
- `lib/autoload.php` — minimal class autoloader (no Composer, no network).
- `cartridges/` — capsule specs (`*.qcap.json`) and the cartridge database.
- `docs/` — the cartridge schema, the output-format contract, and the previous
  maintainer's field notes and ticket archive (the only record of how the format works).

## Usage

    php /app/bin/qcap.php decode <capsule>
    php /app/bin/qcap.php graph  <capsule>
    php /app/bin/qcap.php solve  <capsule>

`<capsule>` is the spec stem, e.g. `verdant-hollow`. Results are written under `/app/out/`.

## State of the code

The CLI and class structure are wired up, but the core of the library is unimplemented —
the decode, graph, and solve methods are stubs that return empty results. The format they
need to implement is not specified anywhere except the maintainer's notes under `docs/`.
