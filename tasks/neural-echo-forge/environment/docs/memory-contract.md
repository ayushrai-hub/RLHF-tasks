# Memory contract

## Command surface

neural-echo-forge with no arguments runs ingest then export. Subcommands ingest and export run one stage.

Default paths: data root /app/data, ingest staging ledger /app/state/ingest-staging.json, snapshot /app/state/memory-snapshot.json, memory records /app/output/memory-records.json, retrieval index /app/output/retrieval-index.json, memory audit /app/output/memory-audit.json.

Exit 0 on success. Exit 3 when ingest (or the default no-argument run after a successful export) finishes with lines_skipped greater than zero while still writing outputs. The export subcommand exits 0 on success even when the snapshot stores a positive lines_skipped value. Exit 2 on fatal I/O or when export runs without a snapshot.

Replace every output file on each successful stage run.

## Input discovery

Load user profiles from /app/data/profiles/user-profiles.json first and record profiles.json in sources_loaded.

Load tool invocations from /app/data/tool-calls/tool-log.jsonl in file line order and record tool-log.jsonl in sources_loaded.

Load session transcripts from /app/data/sessions/ using load-order.json when present, otherwise sorted basename order. Record each session shard basename in sources_loaded in discovery order without deduplication.

Load memory policy from /app/data/policies/memory-policy.json once; policy file name is not listed in sources_loaded.

Environment variable NEF_SESSIONS_ROOT may point at an absolute directory that replaces /app/data/sessions for ingest only.

## Malformed rows

Skip invalid JSON, missing required fields, empty subject or predicate strings, confidence outside 0.0 through 1.0 inclusive, and unknown tier codes. Blank lines are ignored and do not increment lines_skipped. Increment lines_skipped once per skipped ingest row across profiles, tool-log.jsonl, and session shards.

Rows that increment lines_skipped include: a tool or session line that is not valid JSON; a tool or session row missing anchor_ms; a session row carrying both memory and correction objects; a correction row with an empty targets string; a memory or correction object missing required fields or using an unknown tier; a profile baseline item missing predicate, object, confidence, or tier. Rows that do not increment lines_skipped include: blank JSONL lines; session rows with only text and a valid anchor_ms that carry neither memory nor correction; profile entries with an empty subject string (skip the profile entry without counting a row).

Bundled fixture examples that increment lines_skipped: the third line of /app/data/tool-calls/tool-log.jsonl is invalid JSON; the session-beta.jsonl row at turn_seq 2 with anchor_ms 855 carries both memory and correction objects on one line.

The bundled /app/data fixtures yield lines_skipped 2 on ingest. When lines_skipped is greater than zero, ingest still writes the snapshot and export outputs from valid records, and ingest (or the default run) exits 3 while export alone exits 0.

## discovery_seq assignment

Increment discovery_seq only when ingest appends a candidate memory record from a profile baseline row, tool row, session memory row, or session correction row. Do not increment discovery_seq for blank JSONL lines, text-only session turns, rows that only update reference_anchor_ms, or any row counted in lines_skipped. discovery_seq starts at 0 for the first profile baseline candidate and increases by one for each subsequent appended candidate in ingest discovery order.

## Session row shapes

A session JSONL row may carry a memory object, a correction object, or neither. Memory and correction objects are mutually exclusive on one row. Rows without memory or correction still contribute anchor_ms to reference_anchor_ms when anchor_ms is present and valid.

Tool rows carry memory fields directly at the top level per session-schema.md.

Profile baselines seed memories with anchor_ms 0, discovery_seq 0, and source profile_baseline.

## Pipeline

Ingest resolves conflicts and semantic duplicates, applies retention classification, and writes the snapshot. Export reads the snapshot only and must not re-parse session shards.
