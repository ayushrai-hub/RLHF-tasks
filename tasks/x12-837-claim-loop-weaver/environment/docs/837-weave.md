# X12 837 claim loop weave contract

## Command

```text
claim-weaver              # ingest then export (full refresh)
claim-weaver ingest       # write /app/state/weave-snapshot.json only
claim-weaver export       # read snapshot only; write /app/output/*
```

Subcommand contract: `/app/docs/weave-snapshot.md`.

Reads `/app/data/shards/*.edi`, applies `/app/data/shard-manifest.json` priorities, and writes `/app/output/woven-claims.json`, `/app/output/weave-summary.json`, and `/app/output/errors.log`. Creates `/app/output` and `/app/state` as needed.

| Invocation | Exit when no skips | Exit when `skipped_count > 0` |
|------------|-------------------|-------------------------------|
| `claim-weaver ingest` | `0` | `0` (skipped count stored in snapshot only) |
| `claim-weaver export` | `0` | `3` (still write all output files) |
| `claim-weaver` (default) | `0` | `3` (still write all output files) |

Exit `2` on fatal I/O errors. Replace all three output files on each export or default run.

Only the Go standard library may be imported in the module.

## Input shard format

Each `*.edi` file directly under `/app/data/shards/` contains one or more X12 segments. Segments may be separated by the segment terminator `~` or by newline. Blank lines are ignored.

The first segment in each file must be an `ISA` interchange header. Read delimiters from that ISA:

| Delimiter | Source |
|-----------|--------|
| Element separator | Character at **index 3** (0-based) of the ISA segment body (the fourth character of the segment ID + fixed fields) |
| Component separator | Character at **index 104** (0-based) of the ISA segment body — ISA16 |
| Segment terminator | Tilde `~` |

After the ISA establishes separators for a file, parse every segment in that file with those separators. Each new file re-reads its own ISA.

**ISA length:** The ISA segment body must be at least **105 characters** so ISA16 (component separator at index 104) is present. Shorter ISA bodies fall back to element `*` and component `:` — which breaks pipe-delimited shards.

## Shard manifest

`/app/data/shard-manifest.json` maps basename (e.g. `"biller-east.edi"`) to integer priority. Higher integer wins when two shards contribute the same segment type for the same claim loop position.

## File discovery

- Non-recursive: only `*.edi` directly under `/app/data/shards/`.
- Process files in **byte lexicographic ascending order** of basename.
- Within each file, preserve segment order as read.

## Segment validation

Skip a segment (increment global `skipped_count`) when:

- The segment ID is empty after parsing.
- `CLM` segment has fewer than 2 elements or CLM01 (claim control number) is empty.
- `LX` segment has fewer than 2 elements or LX01 is not a positive integer.
- `SV1` segment has fewer than 2 elements or the procedure composite (SV101) has no usable code (second component when present, otherwise first).
- `NM1` segment has qualifier not in `QC`, `IL`, `82`, `85`.

Log every skipped segment to `/app/output/errors.log` as `<filename>: <original segment text exactly as read from the file, no trimming or normalization>`. Error lines sorted alphabetically by the full log line.

### Orphan segments (valid syntax, missing parent loop)

These rules apply when a segment passes the validation checks above but cannot attach to the current loop state in the file being processed. Evaluate **each segment independently** — do not batch-skip trailing segments after an orphan.

| Segment | Condition | Action |
|---------|-----------|--------|
| `LX` | Valid LX01, but no `CLM` has opened a 2300 claim yet in this file | Skip: increment `skipped_count`, log to errors.log |
| `SV1` | Valid procedure, but no 2300 claim is open **or** no 2400 `LX` is open under the current claim | Skip: increment `skipped_count`, log to errors.log |
| `HI` | No open 2300 claim or no open 2400 loop | Ignore silently (do not increment `skipped_count`, do not log) |

Example: a file containing only `ISA`, then `LX*9`, then `SV1*…` before any `CLM` produces **two** skipped segments (the `LX` and the `SV1`), each logged on its own line.

## NM1 patient name normalization

For `NM1*QC` (patient), replace every U+00A0 (no-break space) with ASCII space `0x20` in NM103 (last name field, element index 3), then apply ASCII trim (spaces only at ends).

## Loop hierarchy (2300 / 2400)

Weave segments into claims grouped by **CLM01** (claim control number):

- `CLM` opens loop **2300** (claim level).
- `NM1`, `REF`, and other non-service segments attach to the current 2300.
- `LX` opens loop **2400** (service line) under the **current** 2300 claim.
- `SV1` and `HI` attach to the **current** 2400 loop under the **current** 2300.

When a valid `LX` or `SV1` arrives without its required parent loop open, apply the orphan-segment rules in **Segment validation** (count, log, and continue parsing — do not suppress subsequent segments).

## Service line ordering

Within each claim, sort service lines by `lx_sequence` (LX01) ascending. When two shards supply the same `(control_number, lx_sequence)` pair, the segment set from the higher-priority shard wins entirely.

## Diagnosis pointer inheritance (state mutation)

Replay is sequential per claim control number: processing service line N updates the inherited diagnosis pointer list that service line N+1 in that claim observes.

For each 2400 loop:

1. If an `HI` segment is present, parse diagnosis codes from each HI element (split on the component separator; use the second component when present, else the first). Assign pointers `1`, `2`, … in element order. This list becomes the new inherited default for subsequent 2400 loops in the same claim until overridden.
2. If `HI` is **omitted**, copy the inherited pointer list from the prior 2400 loop in the same claim (empty on the first line).
3. `SV1` element 7 (0-based index 7) may contain diagnosis pointers as a component-separated list (e.g. `1:2:3`). When present, use those pointers on output. When SV1-7 is empty and HI was omitted, emit the inherited pointer list.

Output each service line with `diagnosis_pointers` as a JSON array of strings (e.g. `["1", "2"]`).

## Frequency supersession

Parse CLM05 (element index 5) as a component-separated composite. The third component (1-based sub-element 3) is the **frequency type code**.

When frequency type code is `7` (replacement) and a `REF*F8*<prior_control>` segment exists on the same claim, **remove** the claim whose control number equals `<prior_control>` from the final output. Apply supersession after all shards are woven; if multiple replacements chain, resolve in control-number sort order.

## Output: woven-claims.json

Top-level object with key `claims` — array sorted by `control_number` ascending.

Each claim object:

| Field | Source |
|-------|--------|
| `control_number` | CLM01 |
| `patient_name` | `NM1*QC` NM103 + ` ` + NM104, normalized |
| `subscriber_id` | `NM1*IL` NM109 when present, else empty string |
| `total_charge` | CLM02 formatted with exactly two decimal places |
| `frequency_code` | Third component of CLM05, or `"1"` when missing |
| `service_lines` | Array sorted by `lx_sequence` |

Each service line object:

| Field | Source |
|-------|--------|
| `lx_sequence` | LX01 as integer |
| `procedure` | Second component of SV101 when present, else first component |
| `charge` | SV102 formatted with exactly two decimal places |
| `diagnosis_pointers` | Per inheritance rules above |

## Output: weave-summary.json

```json
{
  "claim_count": 0,
  "service_line_count": 0,
  "skipped_segments": 0,
  "manifest_fingerprint": "…",
  "errors_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "export_epoch": 1
}
```

`service_line_count` is the sum of all service lines across surviving claims after supersession. After validate confirms the ledger matches the snapshot (see `/app/docs/weave-snapshot.md`), `manifest_fingerprint` must match the snapshot field written at ingest time, `errors_digest` is the lowercase hex SHA-256 of snapshot error lines sorted lexicographically and joined with a newline (when there are no errors, hash the empty payload — the SHA-256 of an empty byte sequence, not a JSON empty-string field value), and `export_epoch` is copied from `/app/state/weave-ledger.json`. When the ledger is absent or does not match, leave `manifest_fingerprint`, `errors_digest`, and `export_epoch` empty or omitted.

## Idempotence

Re-running on unchanged inputs must produce byte-identical output files.
