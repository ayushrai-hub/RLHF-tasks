# Exhibit signing audit

Tooling for the gallery kiosk that decides whether signed exhibit images may be
displayed.

- `bin/audit.sh <catalog|verify|report>` — entry point. Reads the audit contract,
  ensures the Trust Registry is up, and runs the library for one stage, writing the
  stage's JSON under `output/`.
- `lib/media_sig_audit.awk` — the audit library: reconciles the database against the
  Trust Registry, verifies detached signatures with OpenSSL, and classifies images.
- `bin/trust_registry.py`, `bin/start_registry.sh` — the local Trust Registry service
  that holds the authoritative current key state, and a helper that starts it.
- `config/audit_contract.toml` — fixed inputs, the registry endpoint, output
  locations, and verification conventions.
- `config/schemas/` — JSON Schemas for the three emitted documents.
- `docs/signing_policy.md` — the signing and remediation policy.
- `data/exhibit_signing.db` — the stale local image, key, and policy-exception records.
- `registry/` — the frozen snapshot the Trust Registry serves.
- `data/media/`, `data/signatures/`, `data/keys/` — PNG fixtures, detached
  signatures, and PEM public keys.

The three stages build on one another: `catalog` reconciles the database with the
registry, `verify` adds signature evidence, and `report` produces the remediation
decisions.
