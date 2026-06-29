"""Verifier for telecom-plan-revenue-by-tier: run the agent pipeline over the
committed lake and require the final answer plus key intermediates to match the
reference recomputed independently from the lake, while every documented naive
shortcut fails and a hidden-seed lake defeats hardcoding.

The reference here is a from-scratch Python re-implementation of the billing spec:
effective-dated rate-card selection, in-cycle window + de-dup + sentinel on usage,
the corrected billed set (the status restatement overriding subscriptions.csv), the
overage formula, and the day-prorated recurring fee and allowances for subscriptions
that changed plan mid-cycle. It shares no code with the agent's R pipeline, so
agreement is real cross-checking rather than a tautology."""

import csv
import json
import math
import os
import subprocess

APP = "/app"
ANSWER = os.path.join(APP, "answer.json")
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

# Monetary fields are graded on a half-dollar absolute floor rather than a tight
# relative tolerance: the answer is the end of a multi-step pipeline (rate-card
# selection, status corrections, window filter, de-dup, unit conversion, per-period
# overage, mid-cycle fee and allowance proration, tier aggregation) recomputed
# independently, so the two are not 1e-6-equal float-for-float, and a correct pipeline
# may round each subscription's bill to the cent before summing. ABS_TOL absorbs that
# cent-level drift (a few cents across ~1700 subscriptions) while staying orders of
# magnitude below every structural error the tests must still reject: the fanned-out
# naive pipeline, ignoring or over-applying the status corrections, a skipped in-cycle
# window filter, counted retry-duplicate rows, the wrong rate-card version, a skipped
# mid-cycle fee proration, or a skipped allowance proration.
ABS_TOL = 0.5

CYCLE_PREFIX = "2025-03"
CYCLE_START = "2025-03-01"
CYCLE_END = "2025-03-31"
CYCLE_DAYS = 31

PLANS_FILE = "plans.csv"
SUBS_FILE = "subscriptions.csv"
CHANGES_FILE = "plan_changes.csv"
CORRECTIONS_FILE = "subscription_status_corrections.csv"
DATA_FILE = "usage_data_sessions.csv"
VOICE_FILE = "usage_voice_calls.tsv"


def _read(path, delim=","):
    """Read a delimited file into a list of dict rows."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter=delim))


def _cycle_cards(plan_rows, as_of=CYCLE_START):
    """Select, per plan_id, the rate-card row in force for the cycle: the latest
    effective_date that is on or before the cycle start. Rows dated after the cycle
    (a published-but-future card) and retired earlier cards are both passed over."""
    best = {}
    for r in plan_rows:
        if r["effective_date"] > as_of:
            continue
        pid = r["plan_id"]
        if pid not in best or r["effective_date"] > best[pid]["effective_date"]:
            best[pid] = r
    return best


def _latest_cards(plan_rows):
    """Per plan_id, the row with the maximum effective_date overall (ignores the
    as-of cutoff). Selecting this reproduces the 'use the newest published card'
    mistake."""
    best = {}
    for r in plan_rows:
        pid = r["plan_id"]
        if pid not in best or r["effective_date"] > best[pid]["effective_date"]:
            best[pid] = r
    return best


def _collect(sessions, calls, use_window, use_dedup):
    """Per subscription, list each valid in-cycle usage row as (day, amount).

    Data amount is megabytes (bytes / 1e6, the -1 sentinel always excluded); voice
    amount is minutes (seconds / 60). day is the day-of-month parsed from the ts, used
    later to bucket usage into the pre-change and post-change periods. use_window keeps
    only rows whose ts falls in the cycle month; use_dedup counts each session_id /
    call_id once. Setting either flag False reproduces the corresponding naive mistake.
    """
    data_by = {}
    seen_s = set()
    for s in sessions:
        if use_window and s["ts"][:7] != CYCLE_PREFIX:
            continue
        if use_dedup:
            if s["session_id"] in seen_s:
                continue
            seen_s.add(s["session_id"])
        b = int(s["bytes_used"])
        if b >= 0:
            data_by.setdefault(s["subscription_id"], []).append(
                (int(s["ts"][8:10]), b / 1e6)
            )

    voice_by = {}
    seen_c = set()
    for c in calls:
        if use_window and c["ts"][:7] != CYCLE_PREFIX:
            continue
        if use_dedup:
            if c["call_id"] in seen_c:
                continue
            seen_c.add(c["call_id"])
        voice_by.setdefault(c["subscription_id"], []).append(
            (int(c["ts"][8:10]), int(c["duration_sec"]) / 60.0)
        )
    return data_by, voice_by


def _in_cycle_changes(changes):
    """Map subscription_id -> (prev_plan_id, effective_day) for the change rows that
    apply to the cycle: an effective_date inside the cycle month. Non-cycle rows are
    dropped here; the billed filter is applied at billing time."""
    out = {}
    for r in changes:
        if r["effective_date"][:7] != CYCLE_PREFIX:
            continue
        out[r["subscription_id"]] = (r["prev_plan_id"], int(r["effective_date"][8:10]))
    return out


def _corrections(rows, as_of=CYCLE_END):
    """Map subscription_id -> corrected_status for corrections in force this cycle: a
    correction_date on or before the cycle end. Later (post-cycle) restatements are
    ignored. Setting as_of past the cycle end pulls in the noise rows (the naive
    mistake)."""
    out = {}
    for r in rows:
        if r["correction_date"] <= as_of:
            out[r["subscription_id"]] = r["corrected_status"]
    return out


def _effective_status(subs, corrections):
    """Per subscription, the billed status after corrections override subscriptions.csv."""
    return {
        s["subscription_id"]: corrections.get(s["subscription_id"], s["status"])
        for s in subs
    }


def _split(usage_rows, day):
    """Sum a subscription's usage into (before day, day-and-after) buckets."""
    before = sum(v for d, v in usage_rows if d < day)
    after = sum(v for d, v in usage_rows if d >= day)
    return before, after


def _bill(
    subs,
    status_of,
    cards,
    data_by,
    voice_by,
    changes,
    use_fee_proration=True,
    use_alloc_proration=True,
):
    """Apply the billing formula over the billed (ACTIVE-after-corrections) subscriptions.

    The end-of-cycle plan (subscriptions.csv) governs the tier. A billed subscription
    whose change row falls in the cycle has its 31-day cycle split on the effective day
    N into a previous-plan period (days 1..N-1) and a new-plan period (days N..31):
    both the recurring fee and each included allowance are day-prorated across the two
    periods, and each period's usage is charged overage against that period's prorated
    allowance at that period's own rate. use_fee_proration False charges the full
    new-plan fee; use_alloc_proration False charges the whole cycle's usage against the
    full new-plan allowance. With both False a changed line is billed as if unchanged.
    """
    answer = 0.0
    by_tier = {}
    recurring = 0.0
    data_overage_total = 0.0
    n_active = 0
    for s in subs:
        sid = s["subscription_id"]
        if status_of[sid] != "ACTIVE":
            continue
        n_active += 1
        new = cards[s["plan_id"]]
        tier = new["tier"]
        new_fee = float(new["monthly_fee_usd"])
        dlist = data_by.get(sid, [])
        vlist = voice_by.get(sid, [])

        changed = sid in changes and (use_fee_proration or use_alloc_proration)
        if changed:
            prev_plan, day = changes[sid]
            prev = cards[prev_plan]
            if use_fee_proration:
                fee = (
                    float(prev["monthly_fee_usd"]) * (day - 1) / CYCLE_DAYS
                    + new_fee * (CYCLE_DAYS - (day - 1)) / CYCLE_DAYS
                )
            else:
                fee = new_fee
            if use_alloc_proration:
                w_prev = (day - 1) / CYCLE_DAYS
                w_new = (CYCLE_DAYS - (day - 1)) / CYCLE_DAYS
                d_before, d_after = _split(dlist, day)
                v_before, v_after = _split(vlist, day)
                d_ov = max(
                    0.0, d_before - float(prev["included_data_mb"]) * w_prev
                ) * float(prev["overage_data_per_mb_usd"]) + max(
                    0.0, d_after - float(new["included_data_mb"]) * w_new
                ) * float(new["overage_data_per_mb_usd"])
                v_ov = max(
                    0.0, v_before - float(prev["included_voice_min"]) * w_prev
                ) * float(prev["overage_voice_per_min_usd"]) + max(
                    0.0, v_after - float(new["included_voice_min"]) * w_new
                ) * float(new["overage_voice_per_min_usd"])
            else:
                used_mb = sum(v for _, v in dlist)
                used_min = sum(v for _, v in vlist)
                d_ov = max(0.0, used_mb - float(new["included_data_mb"])) * float(
                    new["overage_data_per_mb_usd"]
                )
                v_ov = max(0.0, used_min - float(new["included_voice_min"])) * float(
                    new["overage_voice_per_min_usd"]
                )
        else:
            fee = new_fee
            used_mb = sum(v for _, v in dlist)
            used_min = sum(v for _, v in vlist)
            d_ov = max(0.0, used_mb - float(new["included_data_mb"])) * float(
                new["overage_data_per_mb_usd"]
            )
            v_ov = max(0.0, used_min - float(new["included_voice_min"])) * float(
                new["overage_voice_per_min_usd"]
            )

        rev = fee + d_ov + v_ov
        answer += rev
        recurring += fee
        data_overage_total += d_ov
        by_tier[tier] = by_tier.get(tier, 0.0) + rev
    return {
        "answer": answer,
        "by_tier": by_tier,
        "recurring_total_usd": recurring,
        "data_overage_total_usd": data_overage_total,
        "n_active_subscriptions": n_active,
    }


def _reference(lake_dir):
    """Independently recompute the billed revenue, the by-tier split, the
    intermediates, and the answers a naive pipeline would produce."""
    plan_rows = _read(os.path.join(lake_dir, PLANS_FILE))
    cards = _cycle_cards(plan_rows)
    subs = _read(os.path.join(lake_dir, SUBS_FILE))
    changes = _in_cycle_changes(_read(os.path.join(lake_dir, CHANGES_FILE)))
    correction_rows = _read(os.path.join(lake_dir, CORRECTIONS_FILE))
    status_of = _effective_status(subs, _corrections(correction_rows))
    raw_status = {s["subscription_id"]: s["status"] for s in subs}
    sessions = _read(os.path.join(lake_dir, DATA_FILE))
    calls = _read(os.path.join(lake_dir, VOICE_FILE), delim="\t")

    data_by, voice_by = _collect(sessions, calls, use_window=True, use_dedup=True)
    ref = _bill(subs, status_of, cards, data_by, voice_by, changes)

    # Naive variant answers, each isolating one skipped step.
    d_nw, v_nw = _collect(sessions, calls, use_window=False, use_dedup=True)
    d_nd, v_nd = _collect(sessions, calls, use_window=True, use_dedup=False)
    ref["answer_no_window"] = _bill(subs, status_of, cards, d_nw, v_nw, changes)[
        "answer"
    ]
    ref["answer_no_dedup"] = _bill(subs, status_of, cards, d_nd, v_nd, changes)[
        "answer"
    ]
    # Ignore the corrections file and bill off the raw subscriptions.csv status.
    ref["answer_no_corrections"] = _bill(
        subs, raw_status, cards, data_by, voice_by, changes
    )["answer"]
    ref["n_active_no_corrections"] = _bill(
        subs, raw_status, cards, data_by, voice_by, changes
    )["n_active_subscriptions"]
    # Apply every correction regardless of date (the post-cycle noise leaks in).
    status_all = _effective_status(subs, _corrections(correction_rows, as_of="9999-99"))
    ref["answer_all_corrections"] = _bill(
        subs, status_all, cards, data_by, voice_by, changes
    )["answer"]
    # Treat changed lines as unchanged: full new-plan fee and allowance, no period split.
    no_pro = _bill(
        subs,
        status_of,
        cards,
        data_by,
        voice_by,
        changes,
        use_fee_proration=False,
        use_alloc_proration=False,
    )
    ref["answer_no_proration"] = no_pro["answer"]
    ref["recurring_no_proration"] = no_pro["recurring_total_usd"]
    # Prorate the fee but miss the allowance split: full new-plan allowance over total usage.
    ref["answer_no_alloc_proration"] = _bill(
        subs, status_of, cards, data_by, voice_by, changes, use_alloc_proration=False
    )["answer"]
    # Wrong rate card: bill everything off the newest published card.
    latest = _latest_cards(plan_rows)
    ref["answer_latest_card"] = _bill(
        subs, status_of, latest, data_by, voice_by, changes
    )["answer"]

    # The headline fan-out trap: recurring fee multiplied by raw session-row count.
    sess_count = {}
    for s in sessions:
        sess_count[s["subscription_id"]] = sess_count.get(s["subscription_id"], 0) + 1
    naive = 0.0
    for s in subs:
        if status_of[s["subscription_id"]] != "ACTIVE":
            continue
        naive += float(cards[s["plan_id"]]["monthly_fee_usd"]) * sess_count.get(
            s["subscription_id"], 0
        )
    ref["naive"] = naive
    return ref


def _run_agent(lake_dir):
    """Run the agent R pipeline against a lake directory via the DATALAKE_DIR override."""
    env = dict(os.environ, DATALAKE_DIR=lake_dir)
    r = subprocess.run(
        ["Rscript", os.path.join(APP, "analysis.R")],
        cwd=APP,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert r.returncode == 0, r.stderr
    with open(ANSWER) as f:
        return json.load(f)


def _close(a, b):
    """Compare a monetary field against the reference on the half-dollar floor."""
    return abs(float(a) - float(b)) <= ABS_TOL


def _close_map(out_map, ref_map):
    """Key-by-key comparison for the by-tier breakdown on the same floor."""
    if set(out_map.keys()) != set(ref_map.keys()):
        return False
    return all(_close(out_map[k], ref_map[k]) for k in ref_map)


def test_output_schema():
    """answer.json carries the final answer, the by-tier map, and the intermediate fields."""
    out = _run_agent(os.path.join(APP, "data"))
    for key in [
        "answer",
        "recurring_total_usd",
        "data_overage_total_usd",
        "n_active_subscriptions",
    ]:
        assert key in out and math.isfinite(float(out[key]))
    assert isinstance(out["by_tier"], dict) and len(out["by_tier"]) == 4
    for tier in ["BRONZE", "SILVER", "GOLD", "UNLIMITED"]:
        assert tier in out["by_tier"] and math.isfinite(float(out["by_tier"][tier]))


def test_final_answer_matches():
    """The final answer matches the reference recomputed from the committed lake.

    The agent pipeline is run on the committed lake here rather than trusting a
    possibly hand-edited answer.json, so a hardcoded answer cannot pass.
    """
    out = _run_agent(os.path.join(APP, "data"))
    ref = _reference(os.path.join(APP, "data"))
    assert _close(out["answer"], ref["answer"])
    assert _close_map(out["by_tier"], ref["by_tier"])


def test_intermediates_match():
    """The key intermediate facts match the reference, catching right-answer-by-wrong-path."""
    out = _run_agent(os.path.join(APP, "data"))
    ref = _reference(os.path.join(APP, "data"))
    assert _close(out["recurring_total_usd"], ref["recurring_total_usd"])
    assert _close(out["data_overage_total_usd"], ref["data_overage_total_usd"])
    assert int(out["n_active_subscriptions"]) == int(ref["n_active_subscriptions"])


def test_proration_changes_recurring():
    """The mid-cycle proration is material: skipping it moves the recurring total well
    past the grading floor, so a pipeline that bills every line its full new-plan fee
    cannot match. This guards the recurring intermediate against a no-op proration."""
    ref = _reference(os.path.join(APP, "data"))
    assert not _close(ref["recurring_no_proration"], ref["recurring_total_usd"])


def test_corrections_change_billed_set():
    """The status corrections are material: billing off the raw subscriptions.csv
    status (ignoring the corrections file) changes both the billed-subscription count
    and the total, and honouring the post-cycle noise corrections changes the total
    again. This guards the corrected billed set against being skipped or over-applied."""
    ref = _reference(os.path.join(APP, "data"))
    assert ref["n_active_no_corrections"] != ref["n_active_subscriptions"]
    assert not _close(ref["answer_no_corrections"], ref["answer"])
    assert not _close(ref["answer_all_corrections"], ref["answer"])


def test_no_forbidden_access():
    """The agent pipeline does not read the verifier tree or hardcode the answer."""
    with open(os.path.join(APP, "analysis.R")) as f:
        src = f.read()
    assert "/tests" not in src


def test_naive_pipeline_fails():
    """Each documented shortcut yields an answer outside tolerance.

    Covers the headline fan-out trap plus every data-quality and billing step the
    codebook requires: skipping the in-cycle window filter, counting retry-duplicate
    rows, billing off the newest rate card instead of the cycle-effective one, ignoring
    the status corrections, skipping the mid-cycle recurring proration, and prorating
    the recurring fee but missing the matching allowance split all move the answer
    beyond the grading floor, so a pipeline that omits any one cannot pass.
    """
    ref = _reference(os.path.join(APP, "data"))
    assert not _close(ref["naive"], ref["answer"])
    assert not _close(ref["answer_no_window"], ref["answer"])
    assert not _close(ref["answer_no_dedup"], ref["answer"])
    assert not _close(ref["answer_latest_card"], ref["answer"])
    assert not _close(ref["answer_no_corrections"], ref["answer"])
    assert not _close(ref["answer_no_proration"], ref["answer"])
    assert not _close(ref["answer_no_alloc_proration"], ref["answer"])


def test_hidden_lake_generalizes():
    """Re-running the agent pipeline on a hidden-seed lake reproduces the recomputed answer."""
    hidden = os.path.join(FIX, "lake_hidden")
    out = _run_agent(hidden)
    ref = _reference(hidden)
    assert _close(out["answer"], ref["answer"])
    assert _close_map(out["by_tier"], ref["by_tier"])
    assert _close(out["recurring_total_usd"], ref["recurring_total_usd"])
    assert _close(out["data_overage_total_usd"], ref["data_overage_total_usd"])
    assert int(out["n_active_subscriptions"]) == int(ref["n_active_subscriptions"])
