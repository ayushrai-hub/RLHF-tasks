# pact r4 — route report contract

## Checker invocation

```bash
ruby /app/environment/cmd/var_check/main.rb --matrix-full --out /app/output/route_audit.json
```

Run `/app/environment/scripts/build_all.sh` first.

## route_fingerprint

For each matrix arm and path kind, compute sha256 over the canonical rebuilt slice bytes:

1. Take the on-disk slice at `var/state/canonical.rt` produced by the daemon for that arm/path.
2. Serialize header fields (magic, epoch, link_id, band_class, row_count) and row bodies exactly as defined in `slice_layout.md`.
3. `route_fingerprint` = lowercase hex digest of the full byte sequence (no separators).

Slice files are written per profile and path kind under `/app/environment/var/state/` as `{profile_key}_{path_kind}.rt` (for example `run_a_uninterrupted.rt`). The `canonical_path` field in each report row points at the slice file used for that row's digest.

Uninterrupted and recovered paths for the same `profile_key` must yield identical digests when the resolver lab is correct.

## band_class tokens

| Value | Meaning |
|-------|---------|
| 0 | Strict validation, no downgrade |
| 1 | Allow insecure on external link only |
| 2 | Downgrade widens internal query-class routing |
| 3 | Full downgrade (invalid for terminal convergence) |

Terminal convergence requires `band_class` ≤ 1 on every recovered row and `internal_leak_count` equal to zero on every matrix row.

## internal_leak_count

Count resolved rows where `qclass_code` = 2 (internal) and `scope_code` = 1 (external link surface). Must be zero after convergence.

## Recovery command

After a destructive reset via `environment/migrations/mig9.sh`, restore anchor bytes before rerunning the checker:

```bash
/app/environment/migrations/mig9.sh --recover /app/environment/fixtures/seed/arena_seed.bin
```

This command is safe to repeat: it copies seed anchor bytes into `var/anchor/` and must not truncate lane epoch anchors. A second `--recover` with the same seed must leave `var/state/canonical.rt` byte-identical to the first successful recovery cycle.

## Report JSON shape

`matrix_runs` is defined as the array of per-profile run records. Each element includes:

| Field | Type | Meaning |
|-------|------|---------|
| `profile_key` | string | Profile label such as `run_a`, `run_c`, or `run_d` |
| `path_kind` | string | `uninterrupted` or `recovered` |
| `route_fingerprint` | string | 64-character lowercase sha256 hex digest of rebuilt slice bytes |
| `band_class` | integer | Effective downgrade band (0–3) |
| `internal_leak_count` | integer | Count of internal query-class rows on external link surfaces |
| `cross_path_match` | integer | Agreement flag between uninterrupted and recovered digests for the profile |
| `canonical_path` | string | Path to the slice file used for the digest |

The var_check matrix checker writes this report after driving all profile arms.

`run_d` means the held-out profile arm that exercises duplicated recovery passes.

## Matrix profiles

Profiles live under `environment/profiles/`. Keys: `run_a`, `run_b` (public smoke), `run_c` (VPN-race reorder), `run_d` (duplicated recovery).
