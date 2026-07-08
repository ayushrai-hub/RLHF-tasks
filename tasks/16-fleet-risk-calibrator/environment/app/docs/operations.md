# Operations Notes

The scorer is designed for an offline dispatch run.
It should not download packages, call a remote model service, or change the input data files.

Recommended local check:

```bash
go test ./...
go run ./cmd/fleetrisk --model /app/config/model.json --policy /app/config/policy.json --calls /app/data/service_calls.csv --windows /app/data/sensor_windows.csv --history /app/data/asset_history.csv --labels /app/data/maintenance_labels.csv --capacity /app/data/site_capacity.csv --out-dir /app/out
```

The report timestamp is supplied by policy.json so repeated runs stay deterministic.
The tool should overwrite its own output files when rerun.
The parts inventory and transfer table are also supplied inside policy.json.
Fatal input problems should be written to stderr with an ERROR: prefix.
