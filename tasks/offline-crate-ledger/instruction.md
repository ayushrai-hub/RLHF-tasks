The `crateledger` CLI in `/app` produces deterministic lockfiles for release workers from a workspace request file and an on-disk package registry. Release workers have reported that the current output is unreliable: feature-gated dependencies are sometimes missing from the lockfile, versions that were yanked still appear in resolved output, and conflict reports do not prevent stale lockfile contents from being overwritten.

Repair the CLI so it follows `/app/docs/resolver-contract.md` and `/app/docs/lock-schema.md`. The tool must work entirely offline and produce identical bytes for identical inputs.

Keep the existing command interface.
