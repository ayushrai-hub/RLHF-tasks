# arrival-audit environment

Build and run:

```bash
go build -o /app/bin/arrival-audit ./driver/
/app/bin/arrival-audit --trace /app/output/arrival_trace.json --workspace /app/data/workspace --fixtures /app/environment/fixtures/wave
```

Reset workspace before audit:

```bash
bash /app/environment/scripts/setup_fanout.sh /app/data/workspace /app/environment/fixtures/wave
```

Bootstrap layered fan-out views with `/app/environment/scripts/setup_fanout.sh`.
Contract formulas and the published entry-probe rule live in `/app/environment/docs/audit_contract.md`.
Workspace paths are described in `/app/environment/docs/workspace_layout.md`.

When rebuilding outside the image build, set `GOCACHE=/tmp/gocache` and `GOMODCACHE=/tmp/gomodcache` if module cache paths are not writable.

Local verifier (inside the container): `bash /tests/test.sh` runs pytest with `--ctrf /logs/verifier/ctrf.json`.
