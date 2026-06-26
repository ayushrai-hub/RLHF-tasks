# R7 protocol fragments (partial)

Internal excerpts only. They are not sufficient alone to rebuild matrix rows.

## Tier classes (names only)

- Class P — path-style keys use prefix `p/`.
- Class U — URI-style keys use prefix `u://`.
- Class R — opaque refs use prefix `r:`.

## Correlation surfaces

Segment material lives under `fixtures/sidecars/`. Checkpoint seeds live under `data/checkpoints/`. Bind rosters live in `data/propagation/bind_scope.toml`. Pass behavior is wired through the import graph under `src/` — correlate fixtures, blobs, and `chain_ref` rather than treating any one file as sufficient.

## Scratch lane warning

Notes under `data/scratch_lane/` are not authoritative.
