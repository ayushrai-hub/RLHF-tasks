# Stage taxonomy (summary)

Full normative definitions live in /app/docs/validation-memo/cryogrid-thermal-review.md.

| Class | Role |
|-------|------|
| SOURCE | Injects initial variance from sigma |
| TRANSFER | Amplifies variance with kappa and epsilon noise |
| SINK | Pass-through aggregation |
| COUPLER | Combines multiple input variances with coupling_gain |
| FEEDBACK | Transfer-like stage that participates in loop gain analysis |

Each stage appears in pipeline.stages with id, class, inputs (array of upstream ids),
and class-specific numeric fields.

The bundled fixture /app/fixtures/cryo-baseline.json illustrates a linear CryoGrid chain.
