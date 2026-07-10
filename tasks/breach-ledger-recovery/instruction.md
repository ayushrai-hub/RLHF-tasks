Security operations recovered a bundle from three Linux hosts after a suspected intrusion. The Go CLI in `/app` is supposed to turn that evidence into a deterministic incident ledger, but the current implementation misses evidence, accepts malformed bundles, and emits unstable artifacts.

Repair the existing command so this invocation works from `/app`:

`go run /app/cmd/breach-ledger --bundle /app/fixtures/omega --output /app/output`

The command must read the bundle, validate it according to `/app/docs/ledger_contract.md`, and write:

- `/app/output/incident_report.json` for the forensics incident report
- `/app/output/attack_timeline.csv`
- `/app/output/iocs.txt`
- `/app/output/remediation_plan.json`

The bundle combines SSH logs including rotated authentication data, web access JSONL, shell histories, cron and systemd snapshots, process and network records, binary audit frames, a SQLite deleted-file catalog, Git events, encoded secret fragments, and a staged archive. Equivalent evidence orderings must produce byte-identical outputs.

Rejected bundles must exit non-zero and still write `incident_report.json` with `status: "rejected"` and the highest-priority error code. Rejected runs must not emit accepted-run artifacts.

The command must compute the report from the evidence and must not mutate the fixture bundle or config manifest files. The contract, output schemas, validation priority, path handling rules, and operational context are documented under `/app/docs`.
