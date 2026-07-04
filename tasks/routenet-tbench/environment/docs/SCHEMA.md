# Database schema

Database name: `routenet`. Owner: `trainer`. Connection details are in
`/app/config/db.json`. The file is a flat JSON object with the keys
`host` (string), `port` (integer), `user` (string), `password` (string)
and `database` (string); both the trainer's Node code and the verifier's
Python code read these same keys directly.

## Tables

### `nodes`

```
column   type      notes
-------- --------- -------------------------------------------------------
id       integer   primary key, stable across rebuilds, contiguous from 0
label    text      human-readable station label
kind     text      one of {"hub", "stop", "transfer"}
```

### `edges`

```
column   type      notes
-------- --------- -------------------------------------------------------
u        integer   foreign key to nodes.id; u < v is NOT enforced
v        integer   foreign key to nodes.id
split    text      one of {"train", "val", "test"}
```

Edges are undirected: each pair appears exactly once in the table, with
`u != v` and with arbitrary orientation. There are no parallel edges.

Use `LEAST(u, v), GREATEST(u, v)` (or any equivalent canonicalisation) when
comparing pairs across the table to itself.

### `splits`

```
column   type      notes
-------- --------- -------------------------------------------------------
name     text      one of {"train", "val", "test"}
count    integer   number of edges in this split; informational
```

A small bookkeeping table that records the size of each split. The
authoritative source for which edges belong to which split is the `split`
column of `edges`.

## Split semantics

- `train` edges define the graph that the model sees at training time.
- `val` edges are held out for validation (AUC reporting).
- `test` edges are held out for a final unbiased estimate.

Negative examples used during training must not collide with edges in any of
the three splits - leakage of `val` or `test` pairs into the negatives makes
the validation/test AUC silently optimistic.

The TRAIN subgraph (edges where `split = 'train'`) defines the graph distance
used by the hard-negative sampler. Distances over `val` or `test` edges are
not considered.

### Hard-negative distance window

When the sampler evaluates whether a pair `(u, v)` is a valid hard negative, it
measures shortest-path distance with undirected BFS **only along train edges**.
The acceptable window is **2 to 3 hops inclusive** (`MIN_HOPS = 2`,
`MAX_HOPS = 3`, mirrored in `/app/config/sampler.json`):

| Distance | Meaning |
| -------- | ------- |
| 1        | Adjacent in the train subgraph — always a train edge, never a negative. |
| 2–3      | Valid hard-negative candidates (must still not appear in any split). |
| ≥ 4      | Too far — excluded from the hard-negative pool. |

Reachability alone is not enough: a pair that is connected only via a path
longer than three train hops must be rejected even if it is not stored as an
edge in the database.
