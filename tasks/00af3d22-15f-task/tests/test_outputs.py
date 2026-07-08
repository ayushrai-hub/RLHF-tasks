"""Behavior checks for the hard shared-tab settlement optimizer."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


DATASETS = [
    ("primary", "/app/input/participants.json", "/app/input/rules.json", os.environ.get("PLAN_PRIMARY", "/tmp/plan_primary.json")),
    ("validation", "/app/input/participants_validation.json", "/app/input/rules.json", os.environ.get("PLAN_VALIDATION", "/tmp/plan_validation.json")),
    ("synthetic", os.environ.get("PARTICIPANTS_SYNTHETIC", "/tmp/participants_synthetic.json"), os.environ.get("RULES_SYNTHETIC", "/tmp/rules_synthetic.json"), os.environ.get("PLAN_SYNTHETIC", "/tmp/plan_synthetic.json")),
    ("corridor", os.environ.get("PARTICIPANTS_CORRIDOR", "/tmp/participants_corridor.json"), os.environ.get("RULES_CORRIDOR", "/tmp/rules_corridor.json"), os.environ.get("PLAN_CORRIDOR", "/tmp/plan_corridor.json")),
    ("negative", os.environ.get("PARTICIPANTS_NEGATIVE", "/tmp/participants_negative.json"), os.environ.get("RULES_NEGATIVE", "/tmp/rules_negative.json"), os.environ.get("PLAN_NEGATIVE", "/tmp/plan_negative.json")),
    ("rebate", os.environ.get("PARTICIPANTS_REBATE", "/tmp/participants_rebate.json"), os.environ.get("RULES_REBATE", "/tmp/rules_rebate.json"), os.environ.get("PLAN_REBATE", "/tmp/plan_rebate.json")),
]

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ascii_sum(value: str) -> int:
    return sum(value.encode("ascii"))


def suffix_number(value: str, prefix: str) -> int:
    if value.startswith(prefix) and value[len(prefix):].isdigit():
        return int(value[len(prefix):])
    return ascii_sum(value)


def base36(value: str) -> int:
    total = 0
    assert value, "empty base36 payload"
    for ch in value.lower():
        idx = ALPHABET.find(ch)
        assert idx >= 0, f"bad base36 digit {ch}"
        total = total * 36 + idx
    return total


def per_unit_fee(debtor: dict, creditor: dict) -> int:
    debtor_number = suffix_number(debtor["id"], "P")
    creditor_number = suffix_number(creditor["id"], "P")
    fee = 10 + ((debtor_number * 17 + creditor_number * 31) % 9)
    if debtor["group"] != creditor["group"]:
        debtor_group = suffix_number(debtor["group"], "team-")
        creditor_group = suffix_number(creditor["group"], "team-")
        fee += 7 + abs(debtor_group - creditor_group)
    return fee


def pair_rebate(debtor: dict, creditor: dict) -> int:
    debtor_number = suffix_number(debtor["id"], "P")
    creditor_number = suffix_number(creditor["id"], "P")
    return 6 + ((debtor_number * 13 + creditor_number * 19 + ascii_sum(debtor["group"]) + ascii_sum(creditor["group"])) % 17)


def decode_gx(token: str) -> dict:
    parts = token.split(":")
    assert len(parts) == 5 and parts[0] == "GX1" and len(parts[4]) == 1
    n = base36(parts[3])
    expected = (n * 29 + ascii_sum(parts[1]) * 3 + ascii_sum(parts[2]) * 5) % 36
    assert parts[4].lower() == ALPHABET[expected], f"bad GX1 check digit {token}"
    return {"from_group": parts[1], "to_group": parts[2], "cap": (n & 31) + 1, "delta": ((n >> 5) & 31) - 12}


def decode_gl(token: str) -> dict:
    parts = token.split(":")
    assert len(parts) == 5 and parts[0] == "GL1" and len(parts[4]) == 1
    n = base36(parts[3])
    expected = (n * 37 + ascii_sum(parts[1]) * 7 + ascii_sum(parts[2]) * 11) % 36
    assert parts[4].lower() == ALPHABET[expected], f"bad GL1 check digit {token}"
    return {"from_group": parts[1], "to_group": parts[2], "cap": (n & 31) + 1, "delta": ((n >> 5) & 63) - 32}


def lanes_for(debtor: dict, creditor: dict, rules: dict) -> list[tuple[int, int]]:
    unit = rules["settlement_unit_cents"]
    cap = rules["max_transfer_cents"] // unit
    cost = per_unit_fee(debtor, creditor)
    for token in rules.get("corridor_tokens", []):
        entry = decode_gx(token)
        if entry["from_group"] == debtor["group"] and entry["to_group"] == creditor["group"]:
            cap = min(cap, entry["cap"])
            cost += entry["delta"]
    lanes = [(cap, cost)]
    for token in rules.get("corridor_lane_tokens", []):
        entry = decode_gl(token)
        if entry["from_group"] == debtor["group"] and entry["to_group"] == creditor["group"]:
            lanes.append((entry["cap"], cost + entry["delta"]))
    return [(cap, cost) for cap, cost in lanes if cap > 0]


def cheapest_pair_fee(units: int, debtor: dict, creditor: dict, rules: dict) -> int:
    total = 0
    left = units
    for cap, cost in sorted(lanes_for(debtor, creditor, rules), key=lambda item: item[1]):
        take = min(left, cap)
        total += take * cost
        left -= take
        if left == 0:
            return total - pair_rebate(debtor, creditor)
    raise AssertionError("transfer exceeds lane capacity")


def unit_costs(debtor: dict, creditor: dict, rules: dict) -> list[int]:
    costs = []
    for cap, cost in sorted(lanes_for(debtor, creditor, rules), key=lambda item: item[1]):
        costs.extend([cost] * cap)
    if costs:
        costs[0] -= pair_rebate(debtor, creditor)
    return costs


@dataclass
class Edge:
    to: int
    rev: int
    cap: int
    cost: int


class MinCostFlow:
    def __init__(self, n: int):
        self.g: list[list[Edge]] = [[] for _ in range(n)]

    def add_edge(self, fr: int, to: int, cap: int, cost: int) -> None:
        fwd = Edge(to, len(self.g[to]), cap, cost)
        rev = Edge(fr, len(self.g[fr]), 0, -cost)
        self.g[fr].append(fwd)
        self.g[to].append(rev)

    def flow(self, source: int, sink: int, need: int) -> int:
        sent = 0
        total = 0
        n = len(self.g)
        while sent < need:
            dist = [10**18] * n
            prev_v = [-1] * n
            prev_e = [-1] * n
            in_queue = [False] * n
            dist[source] = 0
            queue = [source]
            in_queue[source] = True
            head = 0
            while head < len(queue):
                v = queue[head]
                head += 1
                in_queue[v] = False
                for i, edge in enumerate(self.g[v]):
                    if edge.cap <= 0:
                        continue
                    nd = dist[v] + edge.cost
                    if nd < dist[edge.to]:
                        dist[edge.to] = nd
                        prev_v[edge.to] = v
                        prev_e[edge.to] = i
                        if not in_queue[edge.to]:
                            queue.append(edge.to)
                            in_queue[edge.to] = True
            assert prev_v[sink] != -1, "no complete settlement exists"
            add = need - sent
            v = sink
            while v != source:
                edge = self.g[prev_v[v]][prev_e[v]]
                add = min(add, edge.cap)
                v = prev_v[v]
            v = sink
            while v != source:
                edge = self.g[prev_v[v]][prev_e[v]]
                edge.cap -= add
                self.g[v][edge.rev].cap += add
                total += add * edge.cost
                v = prev_v[v]
            sent += add
        return total


def optimal_fee(participants: list[dict], rules: dict) -> int:
    unit = rules["settlement_unit_cents"]
    assert unit > 0 and rules["max_transfer_cents"] > 0 and rules["max_transfer_cents"] % unit == 0
    assert sum(p["balance_cents"] for p in participants) == 0
    debtors = [p for p in participants if p["balance_cents"] < 0]
    creditors = [p for p in participants if p["balance_cents"] > 0]
    total_units = 0
    n = 2 + len(debtors) + len(creditors)
    source, sink = n - 2, n - 1
    mcf = MinCostFlow(n)
    for i, debtor in enumerate(debtors):
        assert debtor["balance_cents"] % unit == 0
        units = -debtor["balance_cents"] // unit
        total_units += units
        mcf.add_edge(source, i, units, 0)
    for j, creditor in enumerate(creditors):
        assert creditor["balance_cents"] % unit == 0
        mcf.add_edge(len(debtors) + j, sink, creditor["balance_cents"] // unit, 0)
    bans = {(p["from"], p["to"]) for p in rules.get("forbidden_pairs", [])}
    for i, debtor in enumerate(debtors):
        for j, creditor in enumerate(creditors):
            if (debtor["id"], creditor["id"]) in bans:
                continue
            for cost in unit_costs(debtor, creditor, rules):
                mcf.add_edge(i, len(debtors) + j, 1, cost)
    return mcf.flow(source, sink, total_units)


def validate_settlement(label: str, participants_path: str, rules_path: str, plan_path: str) -> None:
    participants = load_json(participants_path)["participants"]
    rules = load_json(rules_path)
    plan = load_json(plan_path)
    unit = rules["settlement_unit_cents"]
    by_id = {p["id"]: p for p in participants}

    assert set(plan) == {"settlement_fee_units", "transfers"}
    assert isinstance(plan["settlement_fee_units"], int) and not isinstance(plan["settlement_fee_units"], bool)
    assert isinstance(plan["transfers"], list) and plan["transfers"], f"{label} plan has no transfers"
    assert len(by_id) == len(participants), "participant ids must be unique"

    sent: dict[str, int] = {}
    received: dict[str, int] = {}
    pairs = set()
    order = []
    fee = 0
    bans = {(p["from"], p["to"]) for p in rules.get("forbidden_pairs", [])}

    for transfer in plan["transfers"]:
        assert set(transfer) == {"from", "to", "amount_cents"}
        src, dst, amount = transfer["from"], transfer["to"], transfer["amount_cents"]
        assert src in by_id and dst in by_id
        assert src != dst
        assert isinstance(amount, int) and not isinstance(amount, bool)
        assert amount > 0
        assert amount % unit == 0
        assert by_id[src]["balance_cents"] < 0
        assert by_id[dst]["balance_cents"] > 0
        assert (src, dst) not in pairs
        assert (src, dst) not in bans
        assert amount // unit <= sum(cap for cap, _ in lanes_for(by_id[src], by_id[dst], rules))
        pairs.add((src, dst))
        order.append((src, dst, amount))
        sent[src] = sent.get(src, 0) + amount
        received[dst] = received.get(dst, 0) + amount
        fee += cheapest_pair_fee(amount // unit, by_id[src], by_id[dst], rules)

    assert order == sorted(order), "transfers must be sorted"
    for participant in participants:
        pid = participant["id"]
        balance = participant["balance_cents"]
        if balance < 0:
            assert sent.get(pid, 0) == -balance, f"debtor {pid} not settled"
            assert received.get(pid, 0) == 0
        elif balance > 0:
            assert received.get(pid, 0) == balance, f"creditor {pid} not settled"
            assert sent.get(pid, 0) == 0
        else:
            assert sent.get(pid, 0) == 0 and received.get(pid, 0) == 0

    assert plan["settlement_fee_units"] == fee
    assert fee == optimal_fee(participants, rules), f"{label} fee {fee} is not optimal"


def test_plan_files_exist():
    for label, participants_path, rules_path, plan_path in DATASETS:
        assert os.path.exists(participants_path), f"{label} participant file is missing"
        assert os.path.exists(rules_path), f"{label} rules file is missing"
        assert os.path.exists(plan_path), f"{label} plan file is missing"


def test_plans_are_valid_and_optimal():
    for dataset in DATASETS:
        validate_settlement(*dataset)
