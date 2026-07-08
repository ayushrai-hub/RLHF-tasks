Fix the Go shared-tab optimizer in `/app/src`, then build and run it.

Inputs are `/app/input/participants.json` and `/app/input/rules.json`; output
must be `/app/output/plan.json`:

```json
{"settlement_fee_units": 123, "transfers": [{"from": "P001", "to": "P002", "amount_cents": 4000}]}
```

Positive balances are owed money; negative balances owe money. Every nonzero
participant must settle exactly to zero. Transfers must go debtor to creditor,
be positive multiples of `settlement_unit_cents`, use each `(from,to)` pair at
most once, avoid `forbidden_pairs`, respect default/corridor/parallel-lane
capacities, and be sorted by `from`, then `to`, then `amount_cents`.

Minimize `settlement_fee_units`, not transfer count. The fee model is described
in `/app/docs/format.md`: deterministic base costs, `GX1` corridor tokens,
`GL1` parallel lanes, cheapest-lane aggregation, negative costs, and a one-time
first-unit rebate for every used pair. Malformed tokens, invalid units,
unbalanced ledgers, or infeasible exact settlement must exit nonzero without
emitting a partial plan.

The starter compiles but is greedy and wrong. The verifier recomputes the
optimum from raw inputs and also generates adversarial ledgers with nonstandard
IDs/groups, dense corridors, forbidden cuts, parallel lanes, negative costs,
rebate-sensitive optima, malformed tokens, and infeasible rules. Hard-coded
answers, same-group-first heuristics, plain greedy, and old min-cost-flow
solutions that ignore the first-unit rebate will fail.
