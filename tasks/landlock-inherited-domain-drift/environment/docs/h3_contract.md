# trace contract

Output path: `/app/output/h7_trace.json`

## Top-level fields

- `rows` — array of observation rows
- `summary` — object with `row_count` (int), `trace_stamp` (string), and `matrix_seal` (string, 16 lowercase hex chars)

## Row object

| Field | Type |
|-------|------|
| profile | string (`w0_short`, `w0_long`) |
| principal | string (`direct`, `svc`) |
| fixture_tag | string (matches profile) |
| stage_digest_hex | string (64 lowercase hex chars) |
| reach_digest | string (16 lowercase hex chars) |
| self_check_field | string (16 lowercase hex chars) |
| admit_code | string (`open`, `hold`, `shut`) |
| snap_a_mark | string (8 lowercase hex chars) |
| snap_b_mark | string (8 lowercase hex chars) |
| handoff_label | string |
| layer_pick | int (0 or 1) |
| rule_count | int (non-negative) |
| chain_seq | int (non-negative) |

## stage_digest_hex

Full SHA256 hex digest over the bytes of the staged artifact selected for the fixture token line. Selection rules are in `/app/environment/docs/k2_field_rules.md`.

## reach_digest

Sixteen-character lowercase hex prefix derived from envelope and staged bytes per `/app/environment/docs/k2_field_rules.md`.

## self_check_field

Sixteen-character lowercase hex rolling digest from reach digest, handoff label, and rule count per `/app/environment/docs/k2_field_rules.md`.

## admit_code

Admission label returned for the principal and action pair per `/app/environment/cfg/principal_map.toml`.

## snapshot marks

Eight-character lowercase hex prefixes from snap seed files and the admission label rules in `/app/environment/docs/k2_field_rules.md`.

## chain_seq

Monotonic capture index from the round ledger at round time. See `/app/environment/docs/k2_field_rules.md`.

## Emit row order

After the prescribed round chain, `rows` must appear in this exact order (four entries):

1. `w0_short` / `direct`
2. `w0_short` / `svc`
3. `w0_long` / `direct`
4. `w0_long` / `svc`

## trace_stamp

Constant `h7-v1` on successful emit.

## matrix_seal

Sixteen-character lowercase hex matrix seal computed after emit per `/app/environment/docs/h3_seal.md` (emit-order row lines, FNV-1a 64-bit).

## Verifier notes

Digest regression checks may invoke the `sha256sum` utility. The platform pytest harness may pass the `--ctrf` flag for run reporting. Flow tools support `--help` smoke checks documented in `/app/environment/docs/run_cli.md`.
