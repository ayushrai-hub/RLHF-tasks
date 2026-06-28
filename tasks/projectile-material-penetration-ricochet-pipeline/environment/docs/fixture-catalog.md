# Fixture catalog

| Stack | Purpose |
|-------|---------|
| `simple` | Single soft layer, full penetration |
| `multi-layer` | Two layers, falloff ordering trap |
| `ricochet-trap` | Hard front layer partial stop |
| `material-id-trap` | `physics_id` vs `asset_label` mismatch |
| `boundary-double` | Multi-layer path ledger boundary debit |
| `thin-glass` | Low energy partial penetration |

| Batch | Purpose |
|-------|---------|
| `two-tick` | Basic tick grouping |
| `tick-order-trap` | Events listed out of tick order |

Materials: `/app/fixtures/materials/catalog.json`

Seeds scale entry velocity magnitude only (see `/app/fixtures/seeds.json`).
