Build the Go HTTP service for terminator-pass-aware orbital contact determination under `/app`; the server plumbing is already present, and the deterministic visibility solver stub in `/app/src/orbit/model.go` must be completed.

The service is built with `make clean && make build`, started by `/app/bin/start.sh`, and must listen on port 8080. The normative schemas, response fields, units, propagation equations, coordinate transforms, Earth-shadow edge cases, sunlit contact clipping rules, terminator crossing event rules, event bracketing rules, output ordering, rounding policy, and error behavior are in `/app/docs/API_SPEC.md`.

Use Go only and the Go standard library only. Do not modify `/tests/`, `/logs/verifier`, or the HTTP route/plumbing files unless a small helper is required by your implementation.
