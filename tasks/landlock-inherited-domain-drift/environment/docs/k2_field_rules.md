# field rules

## Fixture inputs

- w0 short: `/app/environment/fixtures/w0_short.env`
- w0 long: `/app/environment/fixtures/w0_long.env`
- Staged artifact A: `/app/environment/fixtures/stage_a.dat`
- Staged artifact B: `/app/environment/fixtures/stage_b.dat`

Each env file provides `TOKEN=`, `ENVELOPE=`, and `MARKS=` lines.

## layer_pick / staged index

Count whitespace-separated tokens on the `TOKEN=` line. Let `T` be that count.

Read the `MARKS=` value as a string. When the last character is an odd decimal digit (`1`, `3`, `5`, `7`, or `9`), the pick threshold is **4**; otherwise the threshold is **5**.

When `T` is greater than or equal to the threshold, `layer_pick` is **1** and staged artifact B is used. Otherwise `layer_pick` is **0** and staged artifact A is used.

## stage_digest_hex

Compute SHA256 over the full byte contents of the selected staged artifact file. Emit as 64 lowercase hexadecimal characters.

## reach_digest

Let `E` be the UTF-8 bytes of the `ENVELOPE=` value without trailing newline. Let `S` be the raw byte contents of the selected staged artifact. For profile `w0_long` only, when `/app/work/profile_carry.txt` exists after the prescribed round chain, append the file body (trim trailing newline) as UTF-8 suffix bytes `C` before hashing. Compute SHA256 over `E || S` for short-profile rows and `E || S || C` for long-profile rows once carry is established. The `reach_digest` is the first **16** lowercase hex characters of that digest.

## profile_carry

After the `w0_short` / `svc` round completes, persist an eight-character carry prefix derived from the prior `w0_short` / `direct` row `reach_digest` (not `stage_digest_hex`) into `/app/work/profile_carry.txt` as a single line. Long-profile reach steps read this file when present. `h7_drv clear` must remove the carry file together with the round ledger.

## rule_count

Let `M` be the `MARKS=` string. Count characters in `M` that are not whitespace. Add the whitespace-separated token count from the `TOKEN=` line. The sum is `rule_count`.

## self_check_field

Concatenate the UTF-8 bytes of `reach_digest`, `handoff_label`, and the decimal string of `rule_count` with no separators. Compute SHA256 over that byte sequence. The `self_check_field` is the first **16** lowercase hex characters.

## admit_code lookup

Read `/app/environment/cfg/principal_map.toml`. For principal `direct` and action `load`, the route table lists `open`. For principal `svc` with the wrap drop-in active (`nnp_flag = 1`), the route table lists `hold` once enforcement view matches the service route.

## snap_a_mark / snap_b_mark

Read `/app/environment/fixtures/snap_a_seed.txt` and `snap_b_seed.txt` as UTF-8 text (trim trailing newline).

`snap_a_mark` uses SHA256 over `seed_a_bytes || admit_code_utf8` (first 8 lowercase hex chars).

`snap_b_mark` uses the same formula but chooses the admission label for snap B as follows: when the row `reach_digest` already matches the rolling digest implied by `layer_pick` and the fixture envelope, snap B uses the same admission label as snap A; otherwise snap B uses `hold` for principal `svc` and `open` for principal `direct`.

## handoff_label

When exec handoff preserves domain state across principals, rows report `inherited`. Direct rounds pass a non-zero inherit flag into `h7_drv`. Service rounds use launch tag `gnu` and must also pass a non-zero inherit flag through the round wrapper so the exec gate records inherited handoff. When the inherit flag is set or launch semantics preserve domain state, rows report `inherited` rather than `plain`.

## chain_seq

Each `k7_round` invocation captures the current value from `/app/work/round.seq` into the row state, then advances the ledger by one before the next round. The first round after `h7_drv clear` records `chain_seq` **0**; each subsequent prescribed round increments by one.

## Rolling consistency

`reach_digest` must agree with the staged artifact actually selected by `layer_pick` for every fixture after the signing authority binds to staged digests.
