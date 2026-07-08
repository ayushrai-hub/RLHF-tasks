# Run contract — reconciled inventory outputs

This document defines the two artifacts the toolchain under `environment/w7`
must produce, the provenance digest that binds them, and the recovery rule for
the destructive re-sync step. It is the authoritative home for the output
schemas and the digest formula.

## Entry point

Run the pipeline entry point, then the public checker:

```bash
/app/environment/w7/run_entry.sh
/app/environment/r5/inv_verify --all-hosts \
    --inventory-out /app/output/inventory_out.json \
    --report-out    /app/output/reconcile_report.json
```

The verifier runs `pytest` with its standard `--ctrf` report flag; that log is
produced by the harness and is not a deliverable you need to write.

`run_entry.sh` must regenerate both artifacts from the authoritative surfaces on
every run. A statically written artifact, a wrapper around `inv_verify`, or a
stage-only reporter is not a substitute for regenerating through the pipeline.

## Artifact: `/app/output/inventory_out.json`

The canonical inventory. JSON object with keys:

- `schema_version` — integer, `1`.
- `records` — array of surviving host records, one per surviving host, each:
  - `id` — string host id.
  - `role` — string, the surviving role.
  - `region` — string, the surviving region.
  - `provenance` — object:
    - `accepted` — object `{ "surface": <"r1"|"r2"|"r3">, "epoch": <int> }`
      naming the surface and epoch of the claim that survived.
    - `candidates` — array of `{ "surface": <str>, "epoch": <int> }`, one entry
      for every claim that was considered for this host across all surfaces,
      including the ones that lost.
- `retired` — array of removal records, one per host removed by an operator
  retire entry, each `{ "id": <str>, "removed_by": "r3" }`.
- `provenance_digest` — string, the lowercase SHA-256 hex defined below.

## Artifact: `/app/output/reconcile_report.json`

The conflict ledger. JSON object with keys:

- `schema_version` — integer, `1`.
- `ledger` — array, one entry per host seen on any surface (surviving and
  retired), each:
  - `id` — string host id.
  - `accepted_surface` — the surviving surface (`"r1"|"r2"|"r3"`), or `null`
    for a retired host.
  - `role` — the surviving role, or `null` for a retired host.
  - `decision` — a short string tag describing how the host resolved.
  - `candidates` — array of `{ "surface": <str>, "role": <str>, "epoch": <int> }`
    for every claim considered for this host.
  - `removed_by` — present only for a retired host: `"r3"`.
- `binding_digest` — string, the lowercase SHA-256 hex that must equal the
  inventory's `provenance_digest`.

## Provenance digest

Build a canonical byte string, then hash it.

1. For every surviving record, in ascending `id` order, emit one line:

   ```
   H:<id>|R:<role>|G:<region>|S:<accepted.surface>|E:<accepted.epoch>
   ```

2. Then, for every retired record, in ascending `id` order, emit one line:

   ```
   H:<id>|RETIRED|S:<removed_by>
   ```

3. Join the lines with a single `\n` (newline) separator. Do **not** append a
   trailing newline after the last line.

4. `provenance_digest` is the lowercase hexadecimal SHA-256 (the `sha256`
   algorithm, e.g. `sha256sum`) of the UTF-8 bytes of that string.

`binding_digest` in the report is recomputed from the same canonical bytes by
the cross-check driver and must be identical to `provenance_digest`.

## Idempotency and recovery

Reconciliation reads only the authoritative read-only surfaces (`r1`, `r2`,
`r3`), so a repeated run must produce a byte-for-byte identical
`inventory_out.json` and an identical `provenance_digest`.

`environment/r7/rst_step.sh` is a destructive re-sync: running it scrambles the
generated outputs and the pipeline scratch area. **Do not run it again to
recover.** The idempotent recovery command is simply the pipeline entry point:

```bash
/app/environment/w7/run_entry.sh
```

Running `run_entry.sh` rebuilds both artifacts from the read-only surfaces and
is safe to run any number of times; the result is stable across repeats.
