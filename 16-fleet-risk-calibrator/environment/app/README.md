# Fleet Risk Calibrator

This repository contains a small offline scorer for maintenance dispatch planning.

The current build can read the input files and write placeholder reports, but the risk math is incomplete.
The intended command is:

```bash
go run ./cmd/fleetrisk \
  --model /app/config/model.json \
  --policy /app/config/policy.json \
  --calls /app/data/service_calls.csv \
  --windows /app/data/sensor_windows.csv \
  --history /app/data/asset_history.csv \
  --labels /app/data/maintenance_labels.csv \
  --capacity /app/data/site_capacity.csv \
  --out-dir /app/out
```

All inputs are local files.
The model card and output contract are the authoritative operational specs.
