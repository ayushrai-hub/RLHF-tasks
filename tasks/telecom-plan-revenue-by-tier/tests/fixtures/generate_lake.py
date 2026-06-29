"""Deterministic generator for the telecom-plan-revenue-by-tier data lake.

Author-side / verifier-side only. Never copied into the agent image and never run
by tests/test.sh. Emits a 29 file lake (6 authoritative sources + 23 decoys) from a
fixed integer seed, so the committed lake (seed A) and the hidden lake (seed B) come
from one code path. Usage:

    python3 generate_lake.py <seed> <out_dir>

The committed lake is generated with seed 20250301 and the hidden lake with seed
948271; recompute either with the command above.

Conventions baked in here and mirrored by the codebook, the R oracle, and the Python
reference verifier:
  - billing cycle 2025-03 (2025-03-01 .. 2025-03-31), 31 days
  - status in {ACTIVE, SUSPENDED, CANCELLED}; only ACTIVE bills, where the billed
    status is the one after the corrections file is applied (see below)
  - data usage in BYTES; used_mb = sum(bytes_used >= 0) / 1_000_000
  - voice usage in SECONDS; used_min = sum(duration_sec) / 60
  - bytes_used == -1 marks a dropped session, excluded from the data sum
  - usage belongs to the cycle only when its ts falls in 2025-03; the authoritative
    streams also carry adjacent-month (Feb / Apr) rows that must be filtered out
  - a retrying loader duplicates some rows; each session_id / call_id counts once
  - plans.csv is an effective-dated rate card: each plan_id has several rows stamped
    with an effective_date; the row in force for the cycle is the latest one whose
    effective_date is on or before the cycle start (2025-03-01). plans_marketing.csv
    is list price (decoy)
  - subscription_status_corrections.csv is an authoritative restatement of billed
    status: a row whose correction_date is on or before the cycle end (2025-03-31)
    overrides the status in subscriptions.csv for billing. Some ACTIVE lines are
    restated CANCELLED (dropped) and some SUSPENDED / CANCELLED lines are restated
    ACTIVE (added). Rows dated after the cycle end are future restatements and are
    ignored. The corrected-in / corrected-out lines never carry an in-cycle plan
    change, so corrections and proration do not interact.
  - plan_changes.csv is authoritative: a billed subscription whose change row has an
    effective_date inside the cycle has its cycle split on the effective day N into a
    previous-plan period (days 1..N-1) and a new-plan period (days N..31). The new
    plan is the one named in subscriptions.csv and governs the subscription's tier.
    Both the recurring fee AND each included allowance are day-prorated across the two
    periods, and each period's usage (bucketed by the day in its ts) is charged
    overage against that period's prorated allowance at that period's own rate. Change
    rows dated outside the cycle, or for non-billed subscriptions, are noise.

The adjacent-month and duplicate rows are appended by a derived RNG that never
touches the core stream, so the in-cycle, de-duplicated content (and thus the
reference answer) is identical whether or not the contamination pass runs.
"""

import csv
import json
import os
import random
import sys

# Effective-dated rate card. Each plan_id carries three rate rows: a retired card
# (effective 2024-06-01), the card in force for the March 2025 cycle (effective
# 2025-01-01), and a future card that has been published but does not take effect
# until after the cycle (effective 2025-06-01). The cycle-effective card is the one
# whose effective_date is the latest on or before 2025-03-01.
PLAN_VERSIONS = {
    "2024-06-01": [
        {
            "plan_id": "P1",
            "tier": "BRONZE",
            "monthly_fee_usd": 18.00,
            "included_data_mb": 1500,
            "included_voice_min": 250,
            "overage_data_per_mb_usd": 0.012,
            "overage_voice_per_min_usd": 0.060,
        },
        {
            "plan_id": "P2",
            "tier": "SILVER",
            "monthly_fee_usd": 35.00,
            "included_data_mb": 8000,
            "included_voice_min": 800,
            "overage_data_per_mb_usd": 0.010,
            "overage_voice_per_min_usd": 0.050,
        },
        {
            "plan_id": "P3",
            "tier": "GOLD",
            "monthly_fee_usd": 55.00,
            "included_data_mb": 25000,
            "included_voice_min": 2500,
            "overage_data_per_mb_usd": 0.006,
            "overage_voice_per_min_usd": 0.035,
        },
        {
            "plan_id": "P4",
            "tier": "UNLIMITED",
            "monthly_fee_usd": 85.00,
            "included_data_mb": 80000,
            "included_voice_min": 999999,
            "overage_data_per_mb_usd": 0.003,
            "overage_voice_per_min_usd": 0.000,
        },
    ],
    "2025-01-01": [
        {
            "plan_id": "P1",
            "tier": "BRONZE",
            "monthly_fee_usd": 20.00,
            "included_data_mb": 2000,
            "included_voice_min": 300,
            "overage_data_per_mb_usd": 0.010,
            "overage_voice_per_min_usd": 0.050,
        },
        {
            "plan_id": "P2",
            "tier": "SILVER",
            "monthly_fee_usd": 40.00,
            "included_data_mb": 10000,
            "included_voice_min": 1000,
            "overage_data_per_mb_usd": 0.008,
            "overage_voice_per_min_usd": 0.040,
        },
        {
            "plan_id": "P3",
            "tier": "GOLD",
            "monthly_fee_usd": 60.00,
            "included_data_mb": 30000,
            "included_voice_min": 3000,
            "overage_data_per_mb_usd": 0.005,
            "overage_voice_per_min_usd": 0.030,
        },
        {
            "plan_id": "P4",
            "tier": "UNLIMITED",
            "monthly_fee_usd": 90.00,
            "included_data_mb": 100000,
            "included_voice_min": 999999,
            "overage_data_per_mb_usd": 0.002,
            "overage_voice_per_min_usd": 0.000,
        },
    ],
    "2025-06-01": [
        {
            "plan_id": "P1",
            "tier": "BRONZE",
            "monthly_fee_usd": 22.00,
            "included_data_mb": 2500,
            "included_voice_min": 350,
            "overage_data_per_mb_usd": 0.009,
            "overage_voice_per_min_usd": 0.045,
        },
        {
            "plan_id": "P2",
            "tier": "SILVER",
            "monthly_fee_usd": 44.00,
            "included_data_mb": 12000,
            "included_voice_min": 1200,
            "overage_data_per_mb_usd": 0.007,
            "overage_voice_per_min_usd": 0.038,
        },
        {
            "plan_id": "P3",
            "tier": "GOLD",
            "monthly_fee_usd": 66.00,
            "included_data_mb": 35000,
            "included_voice_min": 3500,
            "overage_data_per_mb_usd": 0.004,
            "overage_voice_per_min_usd": 0.028,
        },
        {
            "plan_id": "P4",
            "tier": "UNLIMITED",
            "monthly_fee_usd": 99.00,
            "included_data_mb": 120000,
            "included_voice_min": 999999,
            "overage_data_per_mb_usd": 0.0018,
            "overage_voice_per_min_usd": 0.000,
        },
    ],
}
# Order rows are emitted in: future first, retired last, so neither "first row per
# plan" nor "last row per plan" nor "max effective_date" picks the cycle card.
VERSION_EMIT_ORDER = ["2025-06-01", "2025-01-01", "2024-06-01"]

PLAN_IDS = ["P1", "P2", "P3", "P4"]
PLAN_WEIGHTS = [0.40, 0.32, 0.18, 0.10]
STATUS = ["ACTIVE", "SUSPENDED", "CANCELLED"]
STATUS_WEIGHTS = [0.85, 0.08, 0.07]
N_SUBS = 2000
CYCLE_START = "2025-03-01"
CYCLE_END = "2025-03-31"
CYCLE_DAYS = 31


def _ts(rng, month):
    day = rng.randint(1, 28)
    hh = rng.randint(0, 23)
    mm = rng.randint(0, 59)
    return "2025-%02d-%02dT%02d:%02d:00Z" % (month, day, hh, mm)


def _write_csv(path, rows, header, delim=","):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, delimiter=delim, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)


def _contaminate(seed, subs, data_sessions, voice_calls):
    """Append adjacent-month rows and retry duplicates to the usage streams.

    Uses a derived RNG so the core (in-cycle, unique) rows are untouched: a pipeline
    that filters by the ts window and de-dupes by id reproduces the un-contaminated
    totals exactly, while a pipeline that skips either step overcounts usage and
    overage. Rows are shuffled so the extra rows are not clustered at the file tail.
    """
    crng = random.Random(seed * 7919 + 17)
    core_data = list(data_sessions)
    core_voice = list(voice_calls)

    xid = 0
    for s in subs:
        for _ in range(crng.randint(4, 10)):
            xid += 1
            if crng.random() < 0.5:
                month, day = 2, crng.randint(20, 28)
            else:
                month, day = 4, crng.randint(1, 5)
            data_sessions.append(
                {
                    "subscription_id": s["subscription_id"],
                    "session_id": "X%07d" % xid,
                    "bytes_used": int(crng.lognormvariate(17.2, 0.9)),
                    "ts": "2025-%02d-%02dT%02d:%02d:00Z"
                    % (month, day, crng.randint(0, 23), crng.randint(0, 59)),
                }
            )

    yid = 0
    for s in subs:
        for _ in range(crng.randint(3, 8)):
            yid += 1
            if crng.random() < 0.5:
                month, day = 2, crng.randint(20, 28)
            else:
                month, day = 4, crng.randint(1, 5)
            voice_calls.append(
                {
                    "subscription_id": s["subscription_id"],
                    "call_id": "Y%07d" % yid,
                    "duration_sec": crng.randint(20, 1800),
                    "ts": "2025-%02d-%02dT%02d:%02d:00Z"
                    % (month, day, crng.randint(0, 23), crng.randint(0, 59)),
                }
            )

    for r in crng.sample(core_data, max(1, int(len(core_data) * 0.07))):
        data_sessions.append(dict(r))
    for r in crng.sample(core_voice, max(1, int(len(core_voice) * 0.07))):
        voice_calls.append(dict(r))

    crng.shuffle(data_sessions)
    crng.shuffle(voice_calls)


def _plan_change_rows(rng, subs):
    """Build the plan_changes.csv rows: the authoritative in-cycle ACTIVE changes
    plus out-of-cycle and non-ACTIVE noise that the billing rules must discard.

    The authoritative set is unique per subscription, its new_plan_id matches the
    plan_id recorded in subscriptions.csv, and its prev_plan_id is a different plan,
    so a day-prorated recurring fee genuinely differs from the full new-plan fee.
    """
    rows = []
    active = [s for s in subs if s["status"] == "ACTIVE"]
    changed = rng.sample(active, k=max(1, int(len(active) * 0.12)))
    changed_ids = {s["subscription_id"] for s in changed}
    for s in changed:
        prev = rng.choice([p for p in PLAN_IDS if p != s["plan_id"]])
        # Effective day spans the whole cycle, including the day-1 and day-31 edges
        # where one side of the proration collapses to zero.
        day = rng.randint(1, 31)
        rows.append(
            {
                "subscription_id": s["subscription_id"],
                "prev_plan_id": prev,
                "new_plan_id": s["plan_id"],
                "effective_date": "2025-03-%02d" % day,
            }
        )

    # Noise 1: in-cycle change rows for subscriptions that are not ACTIVE (and so are
    # not billed at all) - must be ignored regardless of date.
    non_active = [s for s in subs if s["status"] != "ACTIVE"]
    for s in rng.sample(non_active, k=min(len(non_active), 120)):
        rows.append(
            {
                "subscription_id": s["subscription_id"],
                "prev_plan_id": rng.choice(PLAN_IDS),
                "new_plan_id": s["plan_id"],
                "effective_date": "2025-03-%02d" % rng.randint(1, 31),
            }
        )

    # Noise 2: out-of-cycle change rows for ACTIVE subscriptions (Jan / Feb / Apr) -
    # the subscription is billed, but the change predates or postdates the cycle and
    # so does not prorate the March fee.
    for s in rng.sample(active, k=min(len(active), 160)):
        if s["subscription_id"] in changed_ids:
            continue
        month = rng.choice([1, 2, 4])
        rows.append(
            {
                "subscription_id": s["subscription_id"],
                "prev_plan_id": rng.choice(PLAN_IDS),
                "new_plan_id": s["plan_id"],
                "effective_date": "2025-%02d-%02d" % (month, rng.randint(1, 27)),
            }
        )

    rng.shuffle(rows)
    return rows


def _status_correction_rows(rng, subs, change_rows):
    """Build subscription_status_corrections.csv: the authoritative restatement of
    billed status that overrides subscriptions.csv.

    Applied corrections (correction_date on or before the cycle end) flip some ACTIVE
    lines to CANCELLED (dropped from billing) and some SUSPENDED / CANCELLED lines to
    ACTIVE (added to billing). A second block of post-cycle (April) corrections flips
    status the other way and must be ignored - a pipeline that applies them regardless
    of date bills the wrong set. Every subscription appears at most once, and no
    corrected line carries an in-cycle plan change, so corrections never interact with
    proration.
    """
    in_cycle_change_ids = {
        r["subscription_id"]
        for r in change_rows
        if r["effective_date"][:7] == "2025-03"
    }
    eligible_active = [
        s
        for s in subs
        if s["status"] == "ACTIVE" and s["subscription_id"] not in in_cycle_change_ids
    ]
    eligible_non_active = [
        s
        for s in subs
        if s["status"] != "ACTIVE" and s["subscription_id"] not in in_cycle_change_ids
    ]

    rows = []
    used = set()

    # Applied: ACTIVE -> CANCELLED, restated within the cycle, so these lines drop.
    for s in rng.sample(eligible_active, k=max(1, int(len(eligible_active) * 0.05))):
        rows.append(
            {
                "subscription_id": s["subscription_id"],
                "corrected_status": "CANCELLED",
                "correction_date": "2025-03-%02d" % rng.randint(1, 31),
            }
        )
        used.add(s["subscription_id"])

    # Applied: SUSPENDED / CANCELLED -> ACTIVE, so these lines are added to billing at
    # their full new-plan fee (no in-cycle change means no proration).
    pool_in = [s for s in eligible_non_active if s["subscription_id"] not in used]
    for s in rng.sample(pool_in, k=min(len(pool_in), 120)):
        month = rng.choice([1, 2, 3])
        rows.append(
            {
                "subscription_id": s["subscription_id"],
                "corrected_status": "ACTIVE",
                "correction_date": "2025-%02d-%02d" % (month, rng.randint(1, 28)),
            }
        )
        used.add(s["subscription_id"])

    # Noise: post-cycle (April) restatements that flip status the wrong way. A pipeline
    # that honours the correction_date discards them; one that does not bills wrong.
    pool_noise = [s for s in subs if s["subscription_id"] not in used]
    for s in rng.sample(pool_noise, k=min(len(pool_noise), 200)):
        flip = "CANCELLED" if s["status"] == "ACTIVE" else "ACTIVE"
        rows.append(
            {
                "subscription_id": s["subscription_id"],
                "corrected_status": flip,
                "correction_date": "2025-04-%02d" % rng.randint(1, 28),
            }
        )
        used.add(s["subscription_id"])

    rng.shuffle(rows)
    return rows


def generate(seed, out_dir):
    rng = random.Random(seed)
    os.makedirs(out_dir, exist_ok=True)

    subs = []
    for i in range(1, N_SUBS + 1):
        sub_id = "S%05d" % i
        cust_id = "C%05d" % (1000 + i)
        plan_id = rng.choices(PLAN_IDS, weights=PLAN_WEIGHTS, k=1)[0]
        status = rng.choices(STATUS, weights=STATUS_WEIGHTS, k=1)[0]
        subs.append(
            {
                "subscription_id": sub_id,
                "customer_id": cust_id,
                "plan_id": plan_id,
                "status": status,
                "cycle_start": CYCLE_START,
                "cycle_end": CYCLE_END,
            }
        )

    data_sessions = []
    voice_calls = []
    sess_id = 0
    call_id = 0
    for s in subs:
        n_sess = rng.randint(10, 60)
        for _ in range(n_sess):
            sess_id += 1
            if rng.random() < 0.04:
                b = -1
            else:
                b = int(rng.lognormvariate(17.2, 0.9))
            data_sessions.append(
                {
                    "subscription_id": s["subscription_id"],
                    "session_id": "D%07d" % sess_id,
                    "bytes_used": b,
                    "ts": _ts(rng, 3),
                }
            )
        n_calls = rng.randint(5, 40)
        for _ in range(n_calls):
            call_id += 1
            dur = rng.randint(20, 1800)
            voice_calls.append(
                {
                    "subscription_id": s["subscription_id"],
                    "call_id": "V%07d" % call_id,
                    "duration_sec": dur,
                    "ts": _ts(rng, 3),
                }
            )

    change_rows = _plan_change_rows(rng, subs)
    correction_rows = _status_correction_rows(rng, subs, change_rows)

    _contaminate(seed, subs, data_sessions, voice_calls)

    plan_rows = []
    for eff in VERSION_EMIT_ORDER:
        for p in PLAN_VERSIONS[eff]:
            plan_rows.append(
                {
                    "plan_id": p["plan_id"],
                    "tier": p["tier"],
                    "effective_date": eff,
                    "monthly_fee_usd": "%.2f" % p["monthly_fee_usd"],
                    "included_data_mb": p["included_data_mb"],
                    "included_voice_min": p["included_voice_min"],
                    "overage_data_per_mb_usd": p["overage_data_per_mb_usd"],
                    "overage_voice_per_min_usd": p["overage_voice_per_min_usd"],
                }
            )
    _write_csv(
        os.path.join(out_dir, "plans.csv"),
        plan_rows,
        [
            "plan_id",
            "tier",
            "effective_date",
            "monthly_fee_usd",
            "included_data_mb",
            "included_voice_min",
            "overage_data_per_mb_usd",
            "overage_voice_per_min_usd",
        ],
    )
    _write_csv(
        os.path.join(out_dir, "subscriptions.csv"),
        subs,
        [
            "subscription_id",
            "customer_id",
            "plan_id",
            "status",
            "cycle_start",
            "cycle_end",
        ],
    )
    _write_csv(
        os.path.join(out_dir, "plan_changes.csv"),
        change_rows,
        ["subscription_id", "prev_plan_id", "new_plan_id", "effective_date"],
    )
    _write_csv(
        os.path.join(out_dir, "subscription_status_corrections.csv"),
        correction_rows,
        ["subscription_id", "corrected_status", "correction_date"],
    )
    _write_csv(
        os.path.join(out_dir, "usage_data_sessions.csv"),
        data_sessions,
        ["subscription_id", "session_id", "bytes_used", "ts"],
    )
    _write_csv(
        os.path.join(out_dir, "usage_voice_calls.tsv"),
        voice_calls,
        ["subscription_id", "call_id", "duration_sec", "ts"],
        delim="\t",
    )

    _generate_decoys(rng, out_dir, subs)


def _generate_decoys(rng, out_dir, subs):
    sub_ids = [s["subscription_id"] for s in subs]
    cust_ids = [s["customer_id"] for s in subs]

    feb_rows = []
    sid = 0
    for s in rng.sample(subs, k=len(subs) // 2):
        for _ in range(rng.randint(8, 40)):
            sid += 1
            feb_rows.append(
                {
                    "subscription_id": s["subscription_id"],
                    "session_id": "F%07d" % sid,
                    "bytes_used": int(rng.lognormvariate(17.0, 0.9)),
                    "ts": _ts(rng, 2),
                }
            )
    _write_csv(
        os.path.join(out_dir, "usage_data_sessions_feb.csv"),
        feb_rows,
        ["subscription_id", "session_id", "bytes_used", "ts"],
    )

    feb_voice = []
    cid = 0
    for s in rng.sample(subs, k=len(subs) // 2):
        for _ in range(rng.randint(4, 30)):
            cid += 1
            feb_voice.append(
                {
                    "subscription_id": s["subscription_id"],
                    "call_id": "W%07d" % cid,
                    "duration_sec": rng.randint(20, 1800),
                    "ts": _ts(rng, 2),
                }
            )
    _write_csv(
        os.path.join(out_dir, "usage_voice_calls_feb.tsv"),
        feb_voice,
        ["subscription_id", "call_id", "duration_sec", "ts"],
        delim="\t",
    )

    mkt = [
        {
            "plan_id": p["plan_id"],
            "tier": p["tier"],
            "list_price_usd": "%.2f" % (p["monthly_fee_usd"] + 5.0),
            "promo_price_usd": "%.2f" % (p["monthly_fee_usd"] - 3.0),
        }
        for p in PLAN_VERSIONS["2025-01-01"]
    ]
    _write_csv(
        os.path.join(out_dir, "plans_marketing.csv"),
        mkt,
        ["plan_id", "tier", "list_price_usd", "promo_price_usd"],
    )

    rollup = []
    for s in rng.sample(subs, k=len(subs) // 3):
        for mo in ("2025-02", "2025-03"):
            rollup.append(
                {
                    "subscription_id": s["subscription_id"],
                    "cycle": mo,
                    "data_mb_total": round(rng.uniform(500, 40000), 1),
                    "voice_min_total": rng.randint(50, 4000),
                }
            )
    _write_csv(
        os.path.join(out_dir, "usage_rollup_mb.csv"),
        rollup,
        ["subscription_id", "cycle", "data_mb_total", "voice_min_total"],
    )

    customers = [
        {
            "customer_id": s["customer_id"],
            "name": "Customer %s" % s["customer_id"],
            "segment": rng.choice(["CONSUMER", "SMB", "ENTERPRISE"]),
            "signup_date": "20%02d-%02d-%02d"
            % (rng.randint(18, 24), rng.randint(1, 12), rng.randint(1, 28)),
        }
        for s in subs
    ]
    _write_csv(
        os.path.join(out_dir, "customers.csv"),
        customers,
        ["customer_id", "name", "segment", "signup_date"],
    )

    devices = [
        {
            "device_id": "DV%05d" % i,
            "customer_id": rng.choice(cust_ids),
            "model": rng.choice(["A12", "A13", "X9", "Z5", "Lite"]),
            "imei": "".join(str(rng.randint(0, 9)) for _ in range(15)),
        }
        for i in range(1, 1801)
    ]
    _write_csv(
        os.path.join(out_dir, "devices.csv"),
        devices,
        ["device_id", "customer_id", "model", "imei"],
    )

    installments = [
        {
            "installment_id": "IN%05d" % i,
            "customer_id": rng.choice(cust_ids),
            "device_id": "DV%05d" % rng.randint(1, 1800),
            "monthly_amount_usd": "%.2f" % rng.uniform(5, 45),
            "remaining_months": rng.randint(0, 24),
        }
        for i in range(1, 1201)
    ]
    _write_csv(
        os.path.join(out_dir, "device_installments.csv"),
        installments,
        [
            "installment_id",
            "customer_id",
            "device_id",
            "monthly_amount_usd",
            "remaining_months",
        ],
    )

    taxes = [
        {"jurisdiction": j, "tax_rate": r}
        for j, r in [
            ("STATE_A", 0.065),
            ("STATE_B", 0.072),
            ("STATE_C", 0.0),
            ("FEDERAL_USF", 0.0333),
        ]
    ]
    _write_csv(os.path.join(out_dir, "taxes.csv"), taxes, ["jurisdiction", "tax_rate"])

    promos = [
        {
            "promo_code": "PR%03d" % i,
            "discount_usd": "%.2f" % rng.uniform(2, 15),
            "applies_to_tier": rng.choice(["BRONZE", "SILVER", "GOLD", "ALL"]),
        }
        for i in range(1, 41)
    ]
    _write_csv(
        os.path.join(out_dir, "promotions.csv"),
        promos,
        ["promo_code", "discount_usd", "applies_to_tier"],
    )

    autopay = [
        {
            "customer_id": c,
            "autopay_enabled": rng.choice([True, False]),
            "method": rng.choice(["CARD", "ACH", "WALLET"]),
        }
        for c in rng.sample(cust_ids, k=len(cust_ids) // 2)
    ]
    _write_json(os.path.join(out_dir, "autopay.json"), autopay)

    porting = [
        {
            "customer_id": rng.choice(cust_ids),
            "event": rng.choice(["PORT_IN", "PORT_OUT"]),
            "date": _ts(rng, rng.choice([2, 3]))[:10],
        }
        for _ in range(300)
    ]
    _write_json(os.path.join(out_dir, "porting_events.json"), porting)

    tower = [
        {
            "tower_id": "T%04d" % rng.randint(1, 500),
            "subscription_id": rng.choice(sub_ids),
            "rsrp_dbm": rng.randint(-120, -60),
            "ts": _ts(rng, 3),
        }
        for _ in range(4000)
    ]
    _write_csv(
        os.path.join(out_dir, "tower_sessions.csv"),
        tower,
        ["tower_id", "subscription_id", "rsrp_dbm", "ts"],
    )

    cal = [
        {
            "date": "2025-03-%02d" % d,
            "is_weekend": (d % 7 in (1, 2)),
            "is_holiday": False,
        }
        for d in range(1, 32)
    ]
    _write_csv(
        os.path.join(out_dir, "calendar.csv"), cal, ["date", "is_weekend", "is_holiday"]
    )

    adjustments = [
        {
            "adjustment_id": "AD%05d" % i,
            "subscription_id": rng.choice(sub_ids),
            "amount_usd": "%.2f" % (rng.uniform(-20, 20)),
            "reason": rng.choice(["GOODWILL", "DISPUTE", "ERROR"]),
        }
        for i in range(1, 251)
    ]
    _write_csv(
        os.path.join(out_dir, "billing_adjustments.csv"),
        adjustments,
        ["adjustment_id", "subscription_id", "amount_usd", "reason"],
    )

    credits = [
        {
            "credit_note_id": "CN%05d" % i,
            "customer_id": rng.choice(cust_ids),
            "amount_usd": "%.2f" % rng.uniform(1, 30),
            "issued": _ts(rng, 3)[:10],
        }
        for i in range(1, 151)
    ]
    _write_csv(
        os.path.join(out_dir, "credit_notes.csv"),
        credits,
        ["credit_note_id", "customer_id", "amount_usd", "issued"],
    )

    tickets = [
        {
            "ticket_id": "TK%05d" % i,
            "customer_id": rng.choice(cust_ids),
            "category": rng.choice(["BILLING", "NETWORK", "DEVICE", "OTHER"]),
            "opened": _ts(rng, 3)[:10],
        }
        for i in range(1, 601)
    ]
    _write_csv(
        os.path.join(out_dir, "customer_support_tickets.csv"),
        tickets,
        ["ticket_id", "customer_id", "category", "opened"],
    )

    outages = [
        {
            "region": rng.choice(["NORTH", "SOUTH", "EAST", "WEST"]),
            "start": _ts(rng, 3),
            "minutes": rng.randint(5, 240),
        }
        for _ in range(60)
    ]
    _write_json(os.path.join(out_dir, "network_outages.json"), outages)

    roaming = [
        {
            "subscription_id": rng.choice(sub_ids),
            "country": rng.choice(["CA", "MX", "UK", "DE", "JP"]),
            "charge_usd": "%.2f" % rng.uniform(1, 50),
            "ts": _ts(rng, 3),
        }
        for _ in range(500)
    ]
    _write_csv(
        os.path.join(out_dir, "roaming_charges.csv"),
        roaming,
        ["subscription_id", "country", "charge_usd", "ts"],
    )

    sims = [
        {
            "sim_iccid": "8901%015d" % i,
            "status": rng.choice(["ACTIVE", "SPARE", "RETIRED"]),
            "subscription_id": rng.choice(sub_ids + [""]),
        }
        for i in range(1, 1501)
    ]
    _write_csv(
        os.path.join(out_dir, "sim_inventory.csv"),
        sims,
        ["sim_iccid", "status", "subscription_id"],
    )

    addresses = [
        {
            "customer_id": s["customer_id"],
            "city": rng.choice(
                ["Springfield", "Riverton", "Lakeview", "Fairfax", "Glendale"]
            ),
            "state": rng.choice(["A", "B", "C"]),
            "zip": "%05d" % rng.randint(10000, 99999),
        }
        for s in subs
    ]
    _write_csv(
        os.path.join(out_dir, "address_book.csv"),
        addresses,
        ["customer_id", "city", "state", "zip"],
    )

    pay_methods = [
        {
            "customer_id": c,
            "method": rng.choice(["CARD", "ACH", "WALLET"]),
            "last4": "%04d" % rng.randint(0, 9999),
        }
        for c in rng.sample(cust_ids, k=len(cust_ids) // 3)
    ]
    _write_json(os.path.join(out_dir, "payment_methods.json"), pay_methods)

    invoices = [
        {
            "invoice_id": "IV%06d" % i,
            "subscription_id": rng.choice(sub_ids),
            "cycle": "2025-02",
            "total_usd": "%.2f" % rng.uniform(20, 200),
        }
        for i in range(1, 1701)
    ]
    _write_csv(
        os.path.join(out_dir, "invoices_prior.csv"),
        invoices,
        ["invoice_id", "subscription_id", "cycle", "total_usd"],
    )

    history = [
        {
            "subscription_id": rng.choice(sub_ids),
            "snapshot_date": _ts(rng, rng.choice([1, 2]))[:10],
            "status": rng.choice(STATUS),
            "plan_id": rng.choice(PLAN_IDS),
        }
        for _ in range(2500)
    ]
    _write_csv(
        os.path.join(out_dir, "subscriptions_history.csv"),
        history,
        ["subscription_id", "snapshot_date", "status", "plan_id"],
    )


if __name__ == "__main__":
    generate(int(sys.argv[1]), sys.argv[2])
    print("wrote lake to", sys.argv[2])
