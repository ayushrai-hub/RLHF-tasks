The atelier API in `/app` is wired up, but several handlers still return `501 not_implemented`. Fill in the missing Elixir code so the API behavior matches the docs in `/app/docs`, including the exact JSON response fields those docs call out.

The unfinished surface covers piece search and graph views, goldsmith workload/cohort views, assignment, assay and hallmark flows, stage advancement, single and bulk casting, release, bulk hallmarking, lineage/mass attribution, and the audit endpoints. Keep those pieces consistent with the documented state machine and error precedence.

Keep the existing schema, seed data, route table, and tests unchanged. The starter `POST /goldsmiths`, `POST /pieces`, `GET /pieces/:id`, and `GET /health` paths should keep working while you implement the missing endpoints.

Run the app with `bash /app/start.sh`; it listens on port 8080.
