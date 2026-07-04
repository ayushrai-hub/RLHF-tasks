# routenet-link-trainer

A Node.js / TensorFlow.js link-prediction trainer for a small route-network
graph stored in PostgreSQL. The training pipeline is composed of three pieces:

- A loader (`src/lib/db.js`) that talks to the local Postgres instance over
  `pg`.
- A hard-negative sampler (`src/lib/sampler.js`) that picks node pairs to use
  as negative examples during training.
- A trainer (`src/cli/train.js`) that builds node embeddings with `@tensorflow/tfjs`
  and reports AUC on the validation split.

Everything runs locally: there is no external service, no remote dataset, and
no model registry. The graph is seeded into Postgres on first boot by
`scripts/start-system.sh`, which invokes `scripts/load-seed.js` against
`data/nodes.csv` and `data/edges.csv`.

## Layout

```
src/
  cli/        - entrypoints (sample, train)
  lib/        - reusable modules (db, graph, model, metrics, sampler, util)
scripts/
  start-system.sh - boots the local Postgres cluster, waits for readiness
  load-seed.js    - one-shot seed loader, invoked by start-system.sh on first boot
  audit.js        - static audit over the sampler source
data/
  nodes.csv       - node table (id, label, kind)
  edges.csv       - edge table (u, v, split)
  snapshot.json   - legacy on-disk graph export (not used by a correct sampler)
docs/
  ARCHITECTURE.md - module map and data flow
  SCHEMA.md       - Postgres schema and split semantics
  AUDIT.md        - description of the static audit rules
config/
  db.json         - Postgres connection settings
  sampler.json    - sampler defaults (k, distance window, etc.)
  trainer.json    - trainer hyperparameters
```

## Running

After `start-system.sh` returns, the trainer and the sampler can be invoked
through their CLIs. Both share the same connection settings from
`config/db.json`.

```
node src/cli/sample.js --seed=7 --k=128 --output=/app/output/negatives.json
node src/cli/train.js  --config=/app/config/trainer.json
```

The static audit is independent of training and can be run at any time:

```
node scripts/audit.js --output=/app/output/audit.json
```
