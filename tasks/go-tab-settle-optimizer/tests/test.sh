#!/usr/bin/env bash
set -uo pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
    exit 1
fi

TESTDIR="$(cd "$(dirname "$0")" && pwd)"

fail() {
    echo "ERROR: $1" >&2
    echo 0 > /logs/verifier/reward.txt
    exit 0
}

cd /app/input || fail "/app/input not found"
sha256sum -c checksums.sha256 || fail "input data checksums do not match"

cd /app/src || fail "/app/src not found"
go build -o /tmp/tabsettle . || fail "agent's code does not compile"

export PLAN_PRIMARY=/tmp/plan_primary.json
export PLAN_VALIDATION=/tmp/plan_validation.json
export PARTICIPANTS_SYNTHETIC=/tmp/participants_synthetic.json
export RULES_SYNTHETIC=/tmp/rules_synthetic.json
export PLAN_SYNTHETIC=/tmp/plan_synthetic.json
export PARTICIPANTS_CORRIDOR=/tmp/participants_corridor.json
export RULES_CORRIDOR=/tmp/rules_corridor.json
export PLAN_CORRIDOR=/tmp/plan_corridor.json
export PARTICIPANTS_NEGATIVE=/tmp/participants_negative.json
export RULES_NEGATIVE=/tmp/rules_negative.json
export PLAN_NEGATIVE=/tmp/plan_negative.json
export PARTICIPANTS_REBATE=/tmp/participants_rebate.json
export RULES_REBATE=/tmp/rules_rebate.json
export PLAN_REBATE=/tmp/plan_rebate.json
export PARTICIPANTS_BAD=/tmp/participants_bad.json
export RULES_BAD_TOKEN=/tmp/rules_bad_token.json
export RULES_INFEASIBLE=/tmp/rules_infeasible.json

python3 - <<'PY'
import json
import os
import random

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"

def b36(n):
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(ALPHABET[r])
    return "".join(reversed(out))

def gx_token(from_group, to_group, max_units, fee_delta):
    payload = ((fee_delta + 12) << 5) | (max_units - 1)
    check = (payload * 29 + sum(from_group.encode()) * 3 + sum(to_group.encode()) * 5) % 36
    return f"GX1:{from_group}:{to_group}:{b36(payload)}:{ALPHABET[check]}"

def gl_token(from_group, to_group, max_units, fee_delta):
    payload = ((fee_delta + 32) << 5) | (max_units - 1)
    check = (payload * 37 + sum(from_group.encode()) * 7 + sum(to_group.encode()) * 11) % 36
    return f"GL1:{from_group}:{to_group}:{b36(payload)}:{ALPHABET[check]}"

def write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")

rng = random.Random(41729)

balances = []
for _ in range(42):
    amount = rng.choice([500, 1000, 1500, 2000, 2500, 3500, 4500, 6000, 8500])
    balances.extend([-amount, amount])
rng.shuffle(balances)
participants = []
for i, balance in enumerate(balances, start=1):
    pid = f"guest-{i:03d}" if i % 13 == 0 else f"P{i:03d}"
    group = f"pod_{i % 7}" if i % 17 == 0 else f"team-{((i * 5) % 8) + 1:02d}"
    participants.append({"id": pid, "balance_cents": balance, "group": group})
write(os.environ["PARTICIPANTS_SYNTHETIC"], {"participants": participants})
write(os.environ["RULES_SYNTHETIC"], {
    "max_transfer_cents": 2500,
    "settlement_unit_cents": 500,
    "forbidden_pairs": [],
    "corridor_tokens": [
        gx_token("team-01", "team-02", 2, -5),
        gx_token("team-03", "team-04", 1, 10),
        gx_token("pod_3", "team-05", 3, -9),
    ],
    "corridor_lane_tokens": [
        gl_token("team-01", "team-02", 4, -23),
        gl_token("pod_3", "team-05", 2, -28),
        gl_token("team-08", "team-07", 3, 12),
    ],
})

participants = [
    {"id": "P001", "balance_cents": -3000, "group": "team-01"},
    {"id": "payer-X", "balance_cents": -2500, "group": "team-02"},
    {"id": "P003", "balance_cents": -2000, "group": "team-05"},
    {"id": "P101", "balance_cents": 2500, "group": "team-04"},
    {"id": "credit-Z", "balance_cents": 3000, "group": "team-01"},
    {"id": "P103", "balance_cents": 2000, "group": "team-02"},
]
write(os.environ["PARTICIPANTS_CORRIDOR"], {"participants": participants})
write(os.environ["RULES_CORRIDOR"], {
    "max_transfer_cents": 2000,
    "settlement_unit_cents": 500,
    "forbidden_pairs": [
        {"from": "P001", "to": "credit-Z"},
        {"from": "payer-X", "to": "P103"},
    ],
    "corridor_tokens": [
        gx_token("team-01", "team-04", 6, -5),
        gx_token("team-02", "team-01", 2, 8),
        gx_token("team-05", "team-02", 1, -1),
    ],
    "corridor_lane_tokens": [
        gl_token("team-01", "team-04", 2, -21),
        gl_token("team-02", "team-01", 5, -8),
        gl_token("team-05", "team-02", 4, -25),
    ],
})

participants = []
for i in range(1, 24):
    amount = 500 * ((i % 5) + 1)
    participants.append({"id": f"payer-{i:02d}", "balance_cents": -amount, "group": "club"})
    participants.append({"id": f"receiver-{i:02d}", "balance_cents": amount, "group": "club"})
participants.extend([
    {"id": "P900", "balance_cents": -3000, "group": "team-99"},
    {"id": "P901", "balance_cents": 3000, "group": "team-99"},
])
write(os.environ["PARTICIPANTS_NEGATIVE"], {"participants": participants})
write(os.environ["RULES_NEGATIVE"], {
    "max_transfer_cents": 4000,
    "settlement_unit_cents": 500,
    "forbidden_pairs": [
        {"from": "payer-01", "to": "receiver-01"},
        {"from": "payer-02", "to": "receiver-03"},
    ],
    "corridor_tokens": [
        gx_token("club", "club", 8, -12),
        gx_token("team-99", "team-99", 8, -12),
        gx_token("club", "team-99", 1, 15),
    ],
    "corridor_lane_tokens": [
        gl_token("club", "club", 5, -30),
        gl_token("team-99", "team-99", 3, -28),
    ],
})

write(os.environ["PARTICIPANTS_REBATE"], {"participants": [
    {"id": "P001", "balance_cents": -1000, "group": "team-01"},
    {"id": "P002", "balance_cents": -1000, "group": "team-01"},
    {"id": "P007", "balance_cents": 1000, "group": "team-01"},
    {"id": "P003", "balance_cents": 1000, "group": "team-01"},
]})
write(os.environ["RULES_REBATE"], {
    "max_transfer_cents": 1000,
    "settlement_unit_cents": 500,
    "forbidden_pairs": [],
    "corridor_tokens": [],
    "corridor_lane_tokens": [],
})

bad = {"participants": [
    {"id": "bad-A", "balance_cents": -1000, "group": "team-X"},
    {"id": "bad-B", "balance_cents": 1000, "group": "team-Y"},
]}
write(os.environ["PARTICIPANTS_BAD"], bad)
write(os.environ["RULES_BAD_TOKEN"], {
    "max_transfer_cents": 1000,
    "settlement_unit_cents": 500,
    "corridor_tokens": ["GX1:team-X:team-Y:zz:not-a-check"],
    "corridor_lane_tokens": [],
    "forbidden_pairs": [],
})
write(os.environ["RULES_INFEASIBLE"], {
    "max_transfer_cents": 500,
    "settlement_unit_cents": 500,
    "corridor_tokens": [gx_token("team-X", "team-Y", 1, 0)],
    "corridor_lane_tokens": [],
    "forbidden_pairs": [{"from": "bad-A", "to": "bad-B"}],
})
PY

/tmp/tabsettle -participants /app/input/participants.json -rules /app/input/rules.json -out "$PLAN_PRIMARY" \
    || fail "solver failed on primary dataset"
/tmp/tabsettle -participants /app/input/participants_validation.json -rules /app/input/rules.json -out "$PLAN_VALIDATION" \
    || fail "solver failed on validation dataset"
/tmp/tabsettle -participants "$PARTICIPANTS_SYNTHETIC" -rules "$RULES_SYNTHETIC" -out "$PLAN_SYNTHETIC" \
    || fail "solver failed on synthetic dataset"
/tmp/tabsettle -participants "$PARTICIPANTS_CORRIDOR" -rules "$RULES_CORRIDOR" -out "$PLAN_CORRIDOR" \
    || fail "solver failed on corridor dataset"
/tmp/tabsettle -participants "$PARTICIPANTS_NEGATIVE" -rules "$RULES_NEGATIVE" -out "$PLAN_NEGATIVE" \
    || fail "solver failed on negative-cost dataset"
/tmp/tabsettle -participants "$PARTICIPANTS_REBATE" -rules "$RULES_REBATE" -out "$PLAN_REBATE" \
    || fail "solver failed on rebate-sensitive dataset"

if /tmp/tabsettle -participants "$PARTICIPANTS_BAD" -rules "$RULES_BAD_TOKEN" -out /tmp/plan_bad.json >/tmp/bad.out 2>/tmp/bad.err; then
    fail "solver accepted malformed corridor token"
fi
if /tmp/tabsettle -participants "$PARTICIPANTS_BAD" -rules "$RULES_INFEASIBLE" -out /tmp/plan_infeasible.json >/tmp/infeasible.out 2>/tmp/infeasible.err; then
    fail "solver accepted infeasible settlement"
fi

cd "$TESTDIR" || fail "test directory vanished"
timeout 180 pytest test_outputs.py -q -rA --tb=short -p no:cacheprovider
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
