# round CLI

Primary flow tool: `/app/environment/tools/k7_round`

Smoke checks use `/app/environment/tools/k7_round --help` and `/app/environment/tools/m4_emit --help`.

Full trace chain (run in order, then emit):

```
/app/environment/d0/h7_drv clear
k7_round --profile w0_short --principal direct
k7_round --profile w0_short --principal svc
k7_round --profile w0_long --principal direct
k7_round --profile w0_long --principal svc
```

Emit tool: `/app/environment/tools/m4_emit`

```
m4_emit --out /app/output/h7_trace.json
```

Run emit only after the round chain needed for the trace matrix. Emit invokes `/app/environment/tooling/seal_trace.sh` to patch `summary.matrix_seal`. Rebuild C sources with `make -C /app/environment all`. Rebuild the stamp binary with `/usr/local/go/bin/go build -o /app/bin/h7stamp ./cmd/h7stamp` from `/app/environment` after Go edits.

Chain reset must clear `/app/work/round.seq` as well as the trace store:

```
/app/environment/d0/h7_drv clear
```

Side probe (optional diagnostics, does not emit trace rows):

```
/app/environment/q8_actor/probe_side.sh note w0_short
```
