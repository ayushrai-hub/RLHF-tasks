Ops needs a reproducible audit of which Ninja outputs rebuild when headers are touched in a scripted order.

Implement `/app/scripts/build_audit.py` per `/app/docs/audit_report_schema.md`. The CLI takes absolute `--fixture` and `--output` paths only, replays each fixture `touch_entries` item with a logged byte offset into `/app/build/.ninja_log`, merges rebuilt output paths, and writes the JSON report. Grading uses absolute fixture paths under `/tests/` in addition to the public sample at `/app/fixtures/touch_order.json`.
