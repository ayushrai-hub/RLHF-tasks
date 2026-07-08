# gatectl workspace notes

## seed.txt

Each sample under `/app/environment/samples/<name>/seed.txt` lists rows as `tag|lane|weight`.

## Commands

`open <workroot> <sample>` copies a sample tree. `offer <workroot> <tag>` stages a new pre-lane row while the gate is open and backing is down; each offer advances the workspace wave and records a carry stamp. Tags are labels, not identities: the stable row and dispatch identity is `(tag, wave)`. `cycle <workroot> [--partial]` performs an interrupted restart that may leave checkpoint material only partly written while durable rows and carry stamps are updated. `raise <workroot>` brings backing up, sets the stash epoch to the current wave, and snapshots barrier generation. `sweep <workroot> [--again]` reconciles waiting rows once backing is up.

## Observation products

`row-obs.jsonl` and `dispatch-obs.jsonl` under `<workroot>/.state/` are derived from held row material, dispatch events, and the visibility rules in `stash-notes.md`. They are not authoritative stores.

## Deferred ledgers

Partial cycles record witnessed deferrals in `<workroot>/.state/defer-witness.bin` and carry stamps in `<workroot>/.state/defer-carry.tab`. The ledgers interact with checkpoint reload, seal epoch progression, barrier generation, and acceptance eligibility for offered rows. See `stash-notes.md`, `carry-notes.md`, and `reconcile.md`.

## Recovery anchor

Mutating commands also maintain a compact recovery anchor under `<workroot>/.state/`. It is crash-recovery material, not an observation product. Warm reload must be able to reconstruct row states, dispatch journal, epochs, carry stamps, and witness entries from the remaining durable material when checkpoint, carry, or witness primary files are stale or absent.

## Build

See `/app/environment/docs/toolchain.md`. Sweep and cycle phase contracts are defined in `/app/environment/docs/reconcile.md`.
