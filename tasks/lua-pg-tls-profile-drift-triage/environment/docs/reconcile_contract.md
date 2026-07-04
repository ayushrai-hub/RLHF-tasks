# TLS remediation manifest contract

## Reference clock

All expiry evaluations use the `reference_clock` date from the YAML profile (`YYYY-MM-DD`).

## Fingerprint canonicalization

Inventory stores bare lowercase `sha256_hex` (64 hex chars). Manifest fingerprints render as lowercase octets separated by colons (`aa:bb:cc:...`).

## Active inventory row

A row is active when:

1. No matching `revocation_events` row exists for its `serial`.
2. `not_after + grace_days >= reference_clock`, where `grace_days` is **14** (see runbook Amendment 7).

## Profile precedence (Amendment 9)

- `bundle.yaml` `trust_anchors` list is authoritative for anchor reconciliation.
- `client.toml` `[client_ca.*]` sections supply service-to-role mappings only; TOML `[trust_anchors.*]` blocks are ignored for report emission.

## inventory_digest

SHA-256 hex digest (no colons) of UTF-8 body formed by sorting active inventory rows by `serial` and joining lines `serial:canonical_fingerprint` separated by newline (`\n`). No trailing newline. The pipeline and independent verification may compute the digest with the `sha256sum` utility. Independent verification may reload bundles via `yaml` and `tomllib` and validate with `jsonschema`.

## Bundled anchor expectations

| anchor_id | enabled | reason |
|-----------|---------|--------|
| live-anchor | true | inventory_match |
| legacy-stale | false | stale_config |
| revoked-slot | false | revoked |
| rollover-phantom | false | stale_config |


Each YAML anchor becomes one record:

| field | type | rule |
|-------|------|------|
| anchor_id | string | from YAML |
| fingerprint | string | canonical config fingerprint |
| enabled | boolean | true only when an active inventory row matches the canonical fingerprint |
| reason | string | `inventory_match`, `revoked`, `stale_config`, or `expired` |

## service_bindings entries

For each `[client_ca.SERVICE]` in TOML, look up the `role_bindings` row where `service_name` matches the service, follow `client_ca_serial` to inventory (do not resolve bindings by indexing active rows on TOML `role_tag` alone), emit:

| field | type |
|-------|------|
| service | string |
| client_ca | string | subject_cn of bound cert |
| fingerprint | string | canonical fingerprint |

Sorted by `service` ascending.

## drift_rows

For each YAML trust anchor, when an inventory row exists for the same canonical fingerprint but the raw config fingerprint string differs from canonical, emit `{source: "yaml", field: "fingerprint", config_value, inventory_value}`. Sort drift rows by the source anchor's `anchor_id` ascending, then by `field` ascending.

## Top-level manifest

| field | value |
|-------|-------|
| api_version | `payments-ingress-tls/1` |
| rollover_epoch | from YAML (`2026-03-15` in bundled data) |
| inventory_digest | per above |
| trust_anchors | array |
| service_bindings | array |
| drift_rows | array |
