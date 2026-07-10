# HTTP surface

`POST http://127.0.0.1:19091/v1/batch-score`

Request JSON keys: `batch_id` (string), `rows` (array of row objects).

Each row object keys: `row_id`, `age` (number or null), `tenure_months` (number or null), `region`, `channel`.

Start the server with `bash /app/environment/ci/start-score-server.sh` after building `/app/bin/score-server`.

Regenerate the audit artifact with `bash /app/environment/scripts/run-batch-audit.sh`.
