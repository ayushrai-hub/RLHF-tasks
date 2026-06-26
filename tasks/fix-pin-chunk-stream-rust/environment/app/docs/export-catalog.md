# Catalog export

`/app/scripts/replay-chunks.sh` writes `/app/data/replay_out/catalog.json`.

The file maps each schedule path relative to `/app/data/traces/` to an array of digest lines for that payload. Keys must cover every `*.trace` file discovered recursively under the trace tree.

`/app/scripts/soak-chunks.sh` must complete two back-to-back catalog exports with identical output.

`make release` installs `/app/bin/streamd`.
