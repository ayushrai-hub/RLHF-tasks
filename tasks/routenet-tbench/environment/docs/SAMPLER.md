# Hard-negative sampler reference

This document describes the sampler CLI as wired in the repository.

## Command line

```
node /app/src/cli/sample.js --seed=<int> --k=<int> --output=<path>
```

The CLI parses three flags from `process.argv` and forwards them to the sampler library. There are no environment-variable overrides.

## Output document

The CLI writes a JSON object to `<path>` with four properties:

- `seed`: the integer passed to `--seed`, echoed back as a JSON number.
- `k`: the integer passed to `--k`, echoed back as a JSON number.
- `source`: a short string label identifying where the edge data came from during sampling.
- `negatives`: a JSON array of length `k`. Each entry is a 2-element array `[u, v]` of integer node identifiers from the `nodes` table.

The trainer reads this document and feeds the `negatives` array into the TensorFlow.js loss as the hard-negative batch for one epoch.

## Static audit

`scripts/audit.js` parses the sampler source and reports violations. See `docs/AUDIT.md` for intent. A clean run produces `audit.json` with top-level fields `status` and `violations`.

## Sampling semantics

Hard negatives are constrained by the train/val/test rules in `docs/SCHEMA.md` and by project configuration in `/app/config/sampler.json`.

### Train-subgraph distance window

Candidates must be **non-edges** whose shortest-path distance in the **train subgraph** (edges where `split = 'train'`) falls in the closed window **[2, 3] hops**:

- `MIN_HOPS = 2` — pairs at distance 1 are actual train edges (or would be too easy).
- `MAX_HOPS = 3` — pairs beyond distance 3 are not “hard” enough for this project.

These bounds are also stored in `/app/config/sampler.json` as `min_hops` and `max_hops`. Distances are computed with undirected BFS over train edges only; val/test edges do not contribute to the adjacency used for distance.

A valid negative `(u, v)` must satisfy all of:

1. `u` and `v` exist in the `nodes` table.
2. `(u, v)` is **not** an edge in **any** split (`train`, `val`, or `test`).
3. The shortest-path distance between `u` and `v` in the train subgraph is **2 or 3**.

### Seed behaviour and determinism

The `--seed` flag drives a **seeded PRNG** (not `Math.random`). The sampler must obey:

- **Determinism:** Running twice with the same `--seed` and `--k` must yield the same **unordered set** of negative pairs (order within the JSON array may differ only if the implementation is otherwise deterministic end-to-end; the verifier compares canonicalised pairs).
- **Seed differentiation:** Two **different** seed values must produce **observably different unordered sets** of negatives when `--k` is held fixed. Reordering the same candidate pool is not sufficient—the selected pairs themselves must change.
- **No post-shuffle override:** Do not apply a fixed sort or tie-break that collapses distinct PRNG streams into identical output sets across seeds.

The default batch settings in `sampler.json` (`seed: 17`, `k: 128`) are illustrative; the verifier exercises multiple seeds and batch sizes.
