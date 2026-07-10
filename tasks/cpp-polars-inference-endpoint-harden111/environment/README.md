# Ridge batch score server

Build with `make -C /app/environment score-server` and install to `/app/bin/score-server`.

The C++ server validates batch requests, probes the Polars sidecar lockfile, invokes the Python feature pipe, and returns ridge scores. Operative preprocessing defaults are ratified in `/app/docs/inference-operations-dossier.md` Section 12.

Start the server: `bash /app/environment/ci/start-score-server.sh`

Run the bundled audit: `bash /app/environment/scripts/run-batch-audit.sh`
