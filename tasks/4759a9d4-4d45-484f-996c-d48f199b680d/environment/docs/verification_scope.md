# Verification Scope

This repair cycle covers CSV row canonicalization, Ed25519 and legacy-bootstrap HMAC verification, hash-chain root computation for `/app/data/ledger_fixture.csv`, and Rack receipt/validate endpoints under `/app/service`.

Ceremony policy sources live under `/app/docs` and `/app/data/key_rotation_notice.json`. Captured rules belong in `/app/output/ceremony_rules.json` for downstream native and Ruby integration work. Enum-like field values must match the machine-readable vocabulary in `/app/docs/ceremony_minutes_addendum.md`.
