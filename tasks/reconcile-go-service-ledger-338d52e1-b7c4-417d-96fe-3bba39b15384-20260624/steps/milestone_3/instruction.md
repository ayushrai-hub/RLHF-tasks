Finish the `/app` API integration. The command below should start an HTTP server:

`go run ./cmd/ledger serve --addr 127.0.0.1:18080`

Keep `/health` returning JSON exactly as `{"ok": true}`. Implement `POST /v1/reports` with body `{"config_path": "...", "events_path": "..."}`. It should build the same summary as milestone 2, store it in memory, and return HTTP 201 with `report_id` and `summary`. The report id must be stable for the same summary: the first 16 lowercase hex chars of the SHA-256 hash of the canonical JSON summary, encoded compactly with no insignificant whitespace and with the same deterministic field/key ordering used in the returned `summary` object.

Implement `GET /v1/reports/{report_id}.csv` to return `text/csv` with header `service,tier,metric,count,sum,min,max,avg,sources`, one row per service/metric sorted by service then metric. Preserve fractional numeric values from the summary instead of truncating or rounding them to integers; for example, an average of `60.5` must appear as `60.5` in both JSON and CSV. Join multiple sources in the CSV `sources` field in alphabetical order with semicolons. Any report id path not found in memory should return 404; malformed `POST /v1/reports` bodies, including invalid JSON or missing required paths, should return 400.
