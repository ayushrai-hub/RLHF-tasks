# Vstamp layout

Boot lane descriptors live under `/app/environment/vstamp_v/` as TOML files referenced by scenario packs.

## lane_class vocabulary

| Stamp | Meaning |
|-------|---------|
| `W` | Warm-lane smoke profile; each `required` id is kept as itself when it appears in the stage-A ingest sink. Rel maps are not applied for substitution. |
| `C` | Cold-boot profile; rel substitution rules below apply to every `required` id. |
| `H` | Held cold variant; same rel substitution rules as `C`. |

## required field

`required` is a list of node ids that must be satisfied in the trimmed bundle for that pack. Lane selection walks `required` in file order and builds the survivor set from the stage-A ingest sink plus the pack rel map in `/app/environment/rel_v/`.

## Rel substitution (C and H lanes only)

When `lane_class` is `C` or `H`, resolve each entry in `required` as follows:

1. If the id is a key in the pack rel map, **drop the source id from the survivor set and replace it with the rel target** (one id in, one id out — not a union of both).
2. Else if the id is present in the stage-A ingest sink, keep that id.
3. Else omit that requirement.

On `W` lanes, step 1 never runs: keep each `required` id that is present in the ingest sink; do not substitute rel targets.

### Transitive rel chains and alias cycles

Follow rel targets transitively until an id has no further mapping or a cycle is detected. On a cycle, keep exactly one survivor: the cycle member with the largest authoritative byte length from the pack `blob_v` table; if several members tie on size, keep the lexicographically smallest id.

The final survivor set is the deduplicated collection of resolved ids, sorted in dependency-respecting order when written to the ledger.

### Illustrative example — cold lane (`demo_cold`)

Inputs (not a graded scenario pack):

- `lane_class = "C"`, `required = ["p0", "p1", "p2"]`
- rel map: `"p2" → "p9"`
- Stage-A ingest sink after closure: `{p0, p1, p2}`

| required id | rel map | survivor id |
|-------------|---------|-------------|
| p0 | — | p0 |
| p1 | — | p1 |
| p2 | p2 → p9 | **p9** (p2 is not kept) |

A common mistake is to keep both `p2` and `p9`; that violates substitution semantics on cold profiles.

### Illustrative example — warm lane (`demo_warm`)

Same `required` list and rel map as `demo_cold`, but `lane_class = "W"`:

| required id | survivor id |
|-------------|---------------|
| p0 | p0 |
| p1 | p1 |
| p2 | p2 |

Rel map entries are ignored on warm lanes.

### Illustrative example — held lane (`demo_held`)

Inputs (not a graded scenario pack):

- `lane_class = "H"`, `required = ["q0", "q1", "q2", "q3"]`
- rel map: `"q2" → "q8"`
- Stage-A ingest sink after closure: `{q0, q1, q2, q3}`

| required id | rel map | survivor id |
|-------------|---------|-------------|
| q0 | — | q0 |
| q1 | — | q1 |
| q2 | q2 → q8 | **q8** (q2 is not kept) |
| q3 | — | q3 |

## node_v seeds and registry

Each `/app/environment/node_v/*_deps.json` file lists `seeds` (entry ids passed to stage A), explicit `nodes` for those seeds, and a `registry` table describing transitive dependency rows that stage A must materialize before lane selection runs when `pk_a.IncSeq()` is non-negative. When `IncSeq() < 0` (poisoned incremental store after `rst7.sh clean` without recover), stage A must **not** expand registry closure—only seed nodes enter the ingest sink, so warm `required` ids that depend on registry-only ancestors are omitted until recover restores a non-negative `seq`. See `/app/environment/docs/q7_contract.md` for incremental-store gating.

## Device-class stamps

Optional `device_class` strings tag packs for matrix reporting only; they do not change digest math.

Do not treat rel maps as authoritative for warm `W` packs when a stub id alone satisfies smoke reachability.
