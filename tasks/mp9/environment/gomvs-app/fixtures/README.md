# Fixtures

Example query inputs for the `gomvs` commands. None load automatically and none
carry expected answers; they are just convenient module and version arguments to
try against the live proxy.

- `queries.json` - a handful of small, well-known modules pinned at exact
  published versions, suitable arguments for `gomod`, `mvs` and `resolve`.
- `escaping.json` - modules whose paths contain uppercase letters, useful for
  checking the proxy path encoding on the `versions` command.

Every published proxy artifact is immutable, so the same arguments return the
same data on every run.
