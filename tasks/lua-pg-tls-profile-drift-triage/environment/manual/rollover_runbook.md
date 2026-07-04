# CA rollover runbook (extract)

## Amendment 7 — expiry grace

After the emergency rollover, treat certificates within **14** calendar days past `not_after` as still active for ingress reconciliation until the reference clock advances beyond that grace band.

## Amendment 9 — profile precedence

When YAML and TOML bundles disagree on trust anchors, the YAML `trust_anchors` stanza in `bundle.yaml` is authoritative. TOML client CA tables only drive service binding rows; do not promote TOML-only anchor blocks into the remediation manifest.

## Draft table (superseded)

Earlier drafts used a 0-day grace window and allowed TOML anchor overrides. Ignore those rows.
