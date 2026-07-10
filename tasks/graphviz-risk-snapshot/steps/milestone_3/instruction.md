There are an Express API and a worker now.
The Express API must validate JWTs strictly and its background worker must record live vulnerability exposure for ledgered dependencies.
The worker must read the CSV dependency ledger, load vulnerabilties from /app/data/<dependency_name>.json for each dependency, normalize each advisory, and submit it to the API.
The solution must output `solve1.js`, `solve2.js`, and `solve3.js`. For milestones 2 and 3, you must also output `worker.js`.

Milestone 3 normative contract:
- The solution script must be runnable directly with `node /app/solve3.js`. When run this way, it must start its own HTTP server on port 8080 and keep running.
- The server must respond to `GET /` for readiness checks, `GET /api/jwt-token` to issue a JWT token, `GET /api/advisory` to read advisories, `POST /api/advisory` to store advisories, and `GET /api/graphviz` for the final snapshot response.
- The API must expose `GET /api/graphviz` and return a JSON object with exactly these top-level fields: `generatedAt`, `findings`, `edges`, `sign`.
- `generatedAt` must be a string in ISO-8601 format.
- `findings` must be the array of normalized advisories produced by the worker.
- `edges` must be an array of two-element arrays describing the graph structure for the risk graph.
- `sign` must be an HMAC-SHA256 signature over the canonical JSON serialization of the object containing only `generatedAt`, `findings`, and `edges`.
- The signing secret is `snapshot-secret-test`.
- The canonical serialization is the JSON string produced with no extra whitespace, using the object key order `generatedAt`, `findings`, `edges` and the same ordering as the JavaScript object literal used to construct the payload.
- The signature must be the hex digest of the HMAC output.
- The worker obtains a JWT from `GET /api/jwt-token` and sends it as the bare value of the `Authorization` header when posting advisories; it should not add a `Bearer ` prefix.