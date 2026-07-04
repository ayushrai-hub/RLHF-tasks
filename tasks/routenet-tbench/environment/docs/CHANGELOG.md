# Changelog

## 0.4.2

- Documented the hard-negative distance window explicitly (`MIN_HOPS = 2`,
  `MAX_HOPS = 3`) in `SAMPLER.md`, `SCHEMA.md`, and `config/sampler.json`.
- Clarified seeded-PRNG invariants: same seed is deterministic; different seeds
  must yield different unordered negative sets.

## 0.4.1

- Restored the static audit's `seeded-randomness` and `no-snapshot-source`
  rules after they were briefly relaxed during the v3 -> v4 migration
  scramble. The audit now mirrors the rules in `AUDIT.md`.

## 0.4.0

- Switched the validation metric from `hits@k` to AUC because the validation
  edge set grew during the v4 rebalance and `hits@k` became unstable.

## 0.3.0

- Added the `data/snapshot.json` cache and updated `src/lib/sampler.js` to
  read it. This made the sampler much faster at the cost of a manual cache
  refresh step that has been forgotten more than once.

## 0.2.0

- Added the `splits` table and switched the trainer to read the split from
  the database. The `data/edges.csv` file is now only used by the seed
  loader the first time Postgres starts; runtime code should read from Postgres instead.

## 0.1.0

- Initial cut: trainer + uniform-random negative sampler, no splits.
