# Material binding

Material properties live in `/app/fixtures/materials/catalog.json`. Each entry includes:

| Field | Meaning |
|-------|---------|
| `physics_id` | Stable numeric id used by simulation and layer records |
| `asset_name` | DCC / asset pipeline display name (not a lookup key) |
| `hardness` | Penetration resistance scalar in `(0, 1]` |
| `falloff` | Energy multiplier applied after fully traversing a layer |

Stack layer records reference materials by **`physics_id` only**. Optional `asset_label` fields on layers are editor metadata and must not override `physics_id` when resolving hardness or falloff.

Resolve materials with `MaterialCatalog::by_physics_id(physics_id)` (or a wrapper that always delegates to it). Do not look up `asset_label` before `physics_id`.

Lookup failures must error; do not silently substitute a default material.
