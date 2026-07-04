# Pipeline overview

The ingress TLS triage stack loads YAML and TOML profile bundles, queries the certificate inventory in PostgreSQL, and emits a remediation manifest for stale trust anchors and service client CA bindings.

Stages:

1. Inventory fetch (`pkg/p48`)
2. Fingerprint normalization (`pkg/w22`)
3. Expiry and grace filtering (`pkg/e17`)
4. Profile merge (`pkg/c91`)
5. Manifest emission (`pkg/r63`)

Contract: `/app/environment/docs/reconcile_contract.md`.

Runbook amendments in `/app/environment/manual/rollover_runbook.md` supersede earlier draft tables.
