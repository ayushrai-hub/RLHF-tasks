# Data formats

## Input: participants.json

```json
{
  "participants": [
    {"id": "P001", "balance_cents": -7500, "group": "team-03"},
    {"id": "P002", "balance_cents": 7500, "group": "team-04"}
  ]
}
```

- `id`: unique participant identifier.
- `balance_cents`: positive means the participant is owed money; negative means
  the participant owes money.
- `group`: participant group used by corridor tokens and cross-group fee terms.

## Input: rules.json

```json
{
  "max_transfer_cents": 2500,
  "settlement_unit_cents": 500,
  "forbidden_pairs": [{"from": "P001", "to": "P002"}],
  "corridor_tokens": ["GX1:team-01:team-02:f6:j"],
  "corridor_lane_tokens": ["GL1:team-01:team-02:1tz:8"]
}
```

- `max_transfer_cents`: default lane capacity before corridor adjustments.
- `settlement_unit_cents`: all balances and transfers are optimized in this
  unit.
- `forbidden_pairs`: exact payer/payee pairs that cannot be used.
- `corridor_tokens`: `GX1` default-lane capacity and fee adjustments.
- `corridor_lane_tokens`: `GL1` extra parallel lanes with separate fee deltas.

Malformed tokens make the input invalid.

## Output: plan.json

```json
{
  "settlement_fee_units": 123,
  "transfers": [
    {"from": "P001", "to": "P002", "amount_cents": 2500}
  ]
}
```

The plan must settle all nonzero participants exactly and report the minimum
possible total fee under all route capacities and lane costs.

## Fees

For participant or group suffixes, use the integer after `P` or `team-`; if that
does not exist, use the ASCII byte sum.

```text
base = 10 + ((debtor_number*17 + creditor_number*31) mod 9)
if groups differ: base += 7 + abs(debtor_group - creditor_group)
```

`GX1:<from_group>:<to_group>:<payload_base36>:<check>` tokens validate with
`(n*29 + ascii(from_group)*3 + ascii(to_group)*5) mod 36`. Matching tokens are
applied in order:

```text
corridor_max_units = (n & 31) + 1
corridor_fee_delta = ((n >> 5) & 31) - 12
```

The default lane capacity is
`min(max_transfer_cents / settlement_unit_cents, matching corridor_max_units...)`;
its cost is `base + sum(matching corridor_fee_delta)`.

`GL1` validates with
`(n*37 + ascii(from_group)*7 + ascii(to_group)*11) mod 36`. Each matching token
adds one parallel lane:

```text
lane_max_units = (n & 31) + 1
lane_fee_delta = ((n >> 5) & 63) - 32
```

The lane cost is the adjusted default cost plus `lane_fee_delta`. When a JSON
transfer uses several lanes for one pair, fill that pair's lanes from lowest
per-unit fee to highest.

For every used pair, subtract this one-time first-unit rebate from the pair's
cheapest filled unit:

```text
rebate = 6 + ((debtor_number*13 + creditor_number*19
             + ascii(debtor_group) + ascii(creditor_group)) mod 17)
```

Adjusted lane costs may be zero or negative.
