# Load and amendment semantics

## Sign conventions

- Beam axis `x` increases from the left node toward the right node (meters).
- Downward vertical force is positive (newtons).
- Sagging bending moment is positive (newton-meters).
- Positive prescribed support settlement is downward (millimeters).
- Rotations follow the right-hand rule about the out-of-plane axis; positive rotation at a support denotes counterclockwise rotation of the right face.

## Units

| Quantity | Unit |
|----------|------|
| Coordinates | meters |
| Forces | newtons |
| Moments | newton-meters |
| Distributed load intensity | newtons per meter |
| Modulus | pascals or gigapascals via `E_pa` / `E_gpa` |
| Inertia | meters⁴ or derived from millimeter section dimensions |
| Deflection output | millimeters |
| Settlement input | millimeters converted to meters internally |

## Amendment commit behavior

- `amendment=accept` applies `replace_segment` and `replace_load_case` directives to committed state and advances the committed revision.
- `amendment=reject` records a rejected stage and leaves committed geometry, loads, and combinations unchanged.
- Rejected stages must not alter numeric results relative to the prior committed revision except for documented provenance counters.

## Coordinate normalization

Replacement load cases name loads in the local coordinate frame of the amended segment identified as `main`. After a `replace_segment` directive, local positions are translated to beam-global coordinates using the accepted segment origin.

## Discontinuity side semantics

At a coordinate carrying both a point moment and a distributed-load boundary, the moment jump applies on the **right** side of the coordinate: the left-limit moment plus the point magnitude defines the right-limit value. Shear follows left-to-right accumulation with distributed resultants applied before point moment jumps at coincident coordinates.

## Combination evaluation

Combinations superpose named load cases with signed factors. Envelope extrema are taken over the combined loading including interior stations, discontinuity sides, and beam endpoints.

## Equilibrium invariants

For simply supported pin-pin spans, comparisons use absolute tolerance `1e-3` unless noted otherwise:

- **Vertical equilibrium:** `left_reaction_n + right_reaction_n` equals the applied vertical force resultant.
- **Global moment about the left support:** `right_reaction_n * span_length` equals the moment of applied **forces** about the left support (point moments are internal and do not enter this resultant check).
- **Pin-pin point load** `F` at `x`: `right_reaction_n = F * x / L`, `left_reaction_n = F - right_reaction_n`.
- **Pin-pin partial UDL** intensity `w` from `x0` to `x1`: resultant `w * (x1 - x0)` at centroid `x0 + (x1 - x0) / 2`, then the same pin-pin formulas on that resultant.

Sample fixture `deck_a` in `/app/environment/fixtures/simple/deck_base.beam` exercises the baseline service combination.

## Numeric policy

Reported envelope scalars round to six decimal places at emission. Comparisons in downstream tooling should use absolute tolerance `1e-3` unless a tighter field-specific tolerance is documented in `/app/environment/docs/report-format.md`.
