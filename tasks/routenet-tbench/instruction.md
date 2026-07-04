The routenet link-prediction stack under `/app` trains on a graph stored in a local PostgreSQL database. Its hard-negative sampler is supposed to draw candidate non-edges from that live graph using the train split only, but the code path that ships today still ingests a frozen on-disk export. Negatives therefore drift from the database: held-out validation and test pairs can appear in training batches, and pairs are no longer “hard” relative to the train subgraph the model actually sees—validation AUC looks fine until you compare against Postgres-grounded sampling.

Repair the sampler implementation under `/app/src/` so the existing CLI and library contract behave as documented in `/app/docs/SAMPLER.md`, with split and distance rules aligned to `/app/docs/SCHEMA.md`. The static audit described in `/app/docs/AUDIT.md` must pass on your final source. Connection settings for the database live in `/app/config/db.json`; you do not need to run the full trainer to validate the fix.

## Distance and seed rules (verifier-aligned)

- **Train-subgraph distance:** A valid hard negative must have shortest-path distance **2 or 3 hops** in the undirected graph formed by **train** edges only (`MIN_HOPS = 2`, `MAX_HOPS = 3` in `/app/config/sampler.json`). Pairs must not be edges in any split (`train`, `val`, or `test`).
- **Seeded PRNG:** Use the `--seed` argument to drive deterministic selection (no `Math.random`). The same `--seed` and `--k` must reproduce the same unordered set of pairs; **different seeds must produce different unordered sets**—not merely a reordering of the same pairs.

## Required output artifacts

When PostgreSQL is running, your solution must leave these files under `/app/output/`:

1. **`negatives.json`** — sampler output with top-level fields:
   - `seed` (integer): echoed from `--seed`
   - `k` (integer): echoed from `--k`
   - `source` (string): must be the literal `"postgres"` for a repaired sampler
   - `negatives` (array): length `k`; each element is `[u, v]` with integer node ids from the live `nodes` table

2. **`audit.json`** — static audit report with:
   - `status` (string): `"ok"` when the repaired sampler source passes
   - `violations` (array): empty on success

Full field semantics and CLI usage are in `/app/docs/SAMPLER.md` and `/app/docs/AUDIT.md`.

Automated verification brings up PostgreSQL and exercises the sampler against the live database. Do not modify the audit script, seed data, or anything under `/app/tests`.
