There are an Express API and a worker now.
The Express API must validate JWTs strictly and its background worker must record live vulnerability exposure for ledgered dependencies.
The worker must read the CSV dependency ledger, load vulnerabilties from /app/data/<dependency_name>.json for each dependency, normalize each advisory, and submit it to the API.
The solution must output `solve1.js`, `solve2.js`, and `solve3.js`. For milestones 2 and 3, you must also output `worker.js`.

Milestone 1 normative contract:
- The solution script must be runnable directly with `node /app/solve1.js`. When run this way, it must start its own HTTP server on port 8080 and keep running.
- The server must respond to `GET /` for readiness checks and to `POST /api/advisory` for the main API contract.
- The request body must be JSON with an object containing an `advisory` field (for example, `{ "advisory": [] }`).
- The request must include an `Authorization` header containing the JWT token. The tests send the token value directly as the header value, not as a `Bearer `-prefixed string.
- The API must verify the JWT strictly using HS256, the secret `ringo-hope`, the issuer `graphviz-risk-snapshot`, and the audience `worker`.
- For a valid JWT, the endpoint must return a JSON object with `{ "success": true }`.
- For an invalid JWT, the endpoint must return a JSON object that does not have `success: true` (typically an error object with HTTP 401).