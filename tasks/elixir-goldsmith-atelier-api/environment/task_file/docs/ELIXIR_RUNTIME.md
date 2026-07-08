# Elixir runtime overview

This service is a small Plug/Cowboy application with handlers under
`/app/lib/goldsmith/handlers`. The database layer is intentionally thin and
uses a single SQLite connection, so endpoint behavior should follow the API
docs and schema rather than introducing a separate persistence model.

The app is expected to run offline from the checked-in Mix project. Do not add
new package downloads at runtime. Keep responses as JSON and keep timestamps in
the UTC format used by the seed data and API specification.

The other files in `/app/docs` define the endpoint contracts, error precedence,
state transitions, seed-data quirks, provenance rules, audit-chain format, and
example request/response shapes.
