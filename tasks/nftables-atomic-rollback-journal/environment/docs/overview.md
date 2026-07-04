# Policy compiler overview

The compiler under `/app/environment` applies rule batches through durable
ledger capture, phase conversion, and window metadata fusion. The audit command
rebuilds `/app/output/audit_report.json` from persisted state and fixtures.

Subsystems:

- `cli/` — audit orchestration helpers
- `cmd/nfrd/` — command entry (`go run /app/environment/cmd/nfrd`)
- `ledger/` — append-only batch capture and segment selection
- `phaseconv/` — phase apply orchestration and view convergence
- `windowfuse/` — epoch metadata merge helpers
- `manifest/` — public layout manifest (`layout.json`)
- `chronicle/`, `phase/` — legacy Python module stubs retained for layout compatibility
- `emit/` — report emission
- `profiles/` — profile registry and fixture routing
- `fixtures/` — per-profile batch inputs
- `tools/` — lane probe helpers; entry at `cmd/laneprobe`

Audit invocation:

```bash
go run /app/environment/cmd/nfrd audit --profile <name>
```

Use `gate`, `depot`, or `yard` for `<name>`. The readiness probe entrypoint
used for yard is:

```bash
go run /app/environment/cmd/laneprobe yard
```

Fixtures seed batch state once per profile. Reruns reuse persisted batch and
epoch files under `/app/output/state/<profile>/`. Verifier tests parse profile
TOML with tomllib and recompute digests with hashlib.

Audit digest fields use sha256 rendered as 64 lowercase hexadecimal characters.
Canonical replay treats rows with the same seq, run_id, phase, rule_id, and
action as duplicates, retaining the highest epoch and then the later source
order. The report counter is the maximum of the layout counter, persisted
counter, and canonical row count after that deduplication.
