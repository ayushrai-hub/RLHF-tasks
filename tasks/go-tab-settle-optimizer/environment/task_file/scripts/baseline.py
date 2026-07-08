#!/usr/bin/env python3
"""Naive non-optimal settlement baseline.

This repeatedly sends money from the largest remaining debtor to the largest
remaining creditor. It ignores forbidden pairs, corridor tokens, parallel
lanes, and the global fee objective, so it is useful only as a quick baseline
for seeing the input shape. It is not a valid solution for the hard task.

    python3 scripts/baseline.py \
        --participants /app/input/participants.json \
        --rules        /app/input/rules.json \
        --out          /tmp/baseline_plan.json
"""
import argparse
import json


def load(path):
    with open(path) as f:
        return json.load(f)


def settle(participants, cap, unit):
    debtors = sorted(
        ([p["id"], -p["balance_cents"]] for p in participants if p["balance_cents"] < 0),
        key=lambda x: -x[1],
    )
    creditors = sorted(
        ([p["id"], p["balance_cents"]] for p in participants if p["balance_cents"] > 0),
        key=lambda x: -x[1],
    )
    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        amt = min(debtors[i][1], creditors[j][1], cap)
        amt = (amt // unit) * unit
        if amt > 0:
            transfers.append({"from": debtors[i][0], "to": creditors[j][0], "amount_cents": amt})
            debtors[i][1] -= amt
            creditors[j][1] -= amt
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1
    return {"settlement_fee_units": sum(t["amount_cents"] // unit for t in transfers), "transfers": transfers}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--participants", required=True)
    ap.add_argument("--rules", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    participants = load(args.participants)["participants"]
    rules = load(args.rules)
    plan = settle(participants, rules["max_transfer_cents"], rules["settlement_unit_cents"])
    with open(args.out, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"wrote {len(plan['transfers'])} transfers to {args.out}")


if __name__ == "__main__":
    main()
