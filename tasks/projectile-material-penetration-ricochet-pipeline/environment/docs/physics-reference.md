# Physics reference (normative)

This page matches verifier ground-truth. Implement `/app/crates/ballcore` to these rules exactly.

## Constants

- Penetration scale `K = 75000`.
- Ricochet stop epsilon `1e-9` on thickness compare.

## Seed scaling

Before integration, scale incident velocity magnitude by the matching entry in `/app/fixtures/seeds.json`. **Do not** scale initial energy `energy_j`.

## Layer loop (in file order)

For each layer with thickness `t`, hardness `h`, falloff `f`, and energy `E` before the layer:

1. `depth = min(t, E / (h × K))`.
2. If `depth < t − 1e−9`, ricochet (see ricochet contract) and stop.
3. Otherwise the layer is fully traversed: add `t` to `path_ledger_m` **once** at the exit boundary.
4. Then set `E = E × f` (falloff applies **after** the layer is fully traversed).
5. Record `depth_m` (6 decimal places), `energy_after_j` (3 decimal places), and flags in the export.

## Rounding

- `path_ledger_m`, `depth_m`: 6 decimal places (half-away-from-zero).
- `exit_energy_j`, `energy_after_j`, angles: 3 decimal places.
