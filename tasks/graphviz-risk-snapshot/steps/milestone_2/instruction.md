There are an Express API and a worker now.
The Express API must validate JWTs strictly and its background worker must record live vulnerability exposure for ledgered dependencies.
The worker must read the CSV dependency ledger, load vulnerabilties from /app/data/<dependency_name>.json for each dependency, normalize each advisory, and submit it to the API.
The solution must output `solve1.js`, `solve2.js`, and `solve3.js`. For milestones 2 and 3, you must also output `worker.js`.

Milestone 2 normative contract:
- The solution script must be runnable directly with `node /app/solve2.js`. When run this way, it must start its own HTTP server on port 8080 and keep running.
- The server must respond to `GET /` for readiness checks, `GET /api/advisory` for reading advisories, and `POST /api/advisory` for storing advisories.
- The API must expose `GET /api/advisory` and return a JSON array of advisory objects.
- The API must expose `POST /api/advisory` and accept a JSON body of the form `{ "advisory": [ ... ] }` and respond with `{ "success": true }`.
- The server must also expose `GET /api/jwt-token`, which returns a JSON object containing a JWT token string. The worker uses this endpoint to obtain a token before posting advisories.
- The worker must submit advisories periodically using the API endpoint above. When posting advisories, it sends the token as the value of the `Authorization` header directly, without adding a `Bearer ` prefix.
- The worker must load OSV.dev advisories for each dependency from /app/data/<dependency_name>.json
- Each normalized advisory object must contain the following required fields:
  - `advisoryId`: string, vulnerability identifier from OSV
  - `name`: string, dependency name
  - `age`: string, ISO-8601 timestamp or equivalent publication timestamp
  - `severity`: string, severity value or `unknown`
- Additional fields may be included, such as `package` and `version`, but the above four fields are the contract that tests validate.