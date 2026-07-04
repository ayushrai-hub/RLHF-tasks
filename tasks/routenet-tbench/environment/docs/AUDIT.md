# Static audit

`scripts/audit.js` reads the sampler source as text and emits a small JSON report. A passing run sets `status` to `"ok"` and leaves `violations` empty; failures list one object per problem found.

The audit is intentionally conservative: it encodes project conventions for how this service is allowed to obtain graph data, drive randomness, and structure negatives. It does **not** execute the sampler or prove correctness against Postgres—that is what the integration verifier does.

At a high level, a healthy sampler implementation:

- obtains graph data through the database layer rather than treating files under `/app/data/` as the authoritative graph;
- uses seeded, reproducible selection when the CLI passes `--seed`;
- does not embed large hand-written negative lists in source; and
- keeps filesystem reads of graph snapshots out of the sampling path.

Rule identifiers in `violations` are stable for CI; see the audit script only if you need to interpret a specific failure message.

## Verifier conventions

The pytest harness may write a machine-readable CTRF report via `pytest-json-ctrf`. That report is for the platform, not something you interact with directly.
