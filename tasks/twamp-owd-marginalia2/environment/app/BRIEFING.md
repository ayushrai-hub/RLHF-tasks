# TWAMP OWD Audit — engineer briefing

A small TWAMP (RFC 5357) one-way-delay reflector audit. The binary at
`/app/bin/auditor` ingests OWD probe records from session-reflectors,
classifies them under the rules spread across this engineering tree,
and emits a single deterministic JSON report at
`/app/output/report.json`.

The TWAMP control plane is out of scope. This is a pure post-hoc
auditor over already-captured probe NDJSON shards plus an operator
markers file.

## Where to read what

The spec is intentionally distributed. Read every page; no single page
is the whole truth. Each subdirectory carves one slice of the
contract:

| Folder                | Slice |
|-----------------------|-------|
| `probe_intake/`       | NDJSON shape, strict-int gating, send_ts magnitude routing |
| `reflector_atlas/`    | Reflector registry layout, classes, offline marking |
| `verdict_ladder/`     | Closed verdict enum, per-probe verdict assignment, zero-emission invariants |
| `owd_fieldbook/`      | Canonical OWD formula, validity window boundaries, staleness ceiling |
| `cycle_journal/`      | Cross-cycle cascade, threshold ladder, quiet-period one-shot marker |
| `digest_workshop/`    | Marker seal recipe, canonical digest bytes, worked digest example |
| `allocator_pages/`    | Largest-remainder allocation, tiebreak direction flip |
| `run_recipe/`         | Pipeline order, output-directory exclusivity, build commands, critical pins |
| `lexicon.txt`         | Domain glossary |
| `revision_notes.md`   | Shape and policy history |
| `docs_index.json`     | Machine-readable table of contents |

## Quick start

```
cd /app
make build      # rebuild /app/bin/auditor from /app/internal source
make verify     # rebuild + run + print one-line summary of key invariants
```

See `run_recipe/build_targets.md` for what each target does and how
to spot-check your fix without paying the full pytest cost.

## Inputs and output

* Inputs: `/app/data/{config.json, reflectors.json, probes_shard_a.ndjson, probes_shard_b.ndjson, markers.ndjson}`.
* Output: `/app/output/report.json` (exactly one file, no leftovers).

The auditor is a pure function of `/app/data`. No logs, no temp files,
no environment-variable state. Re-running with the same input must
produce a byte-identical report.

## Critical pins

For the four pins that round after round trip agents up, read
`run_recipe/critical_pins.md` FIRST. They are restated in detail
elsewhere; the pins file is the truncation-proof short form.
