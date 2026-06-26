# Architecture

## Packages

- `internal/ward` — admission engine and graded tests
- `chorus/chrono` — millisecond window helpers
- `tally/spool` — bundle store and material selection
- `parcel/realm` — realm registry and comparison
- `relay/alias` — external id map
- `meter` — counters (read-only telemetry)
- `relay` — audit relay (observability only)

## Admission pipeline

1. Window check against configured slack
2. Bundle material selection for live generation
3. HMAC validation
4. Realm binding
5. External id resolution against live map generation

See `contract.md` for invariants.
