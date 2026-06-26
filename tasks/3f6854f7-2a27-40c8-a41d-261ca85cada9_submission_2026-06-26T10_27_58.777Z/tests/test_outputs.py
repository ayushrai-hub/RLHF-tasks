import csv
import json
import os
import subprocess
from pathlib import Path


class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


APP = Path("/app")
OUT = APP / "output" / "audit.json"
IDS = APP / "sfdata" / "spec" / "list.txt"
SETS = APP / "sfdata" / "sets"


def _digest(text: str, width: int) -> str:
    script = "const crypto=require('crypto'); process.stdout.write(crypto.createHash('sha256').update(process.argv[1]).digest('hex').slice(0, Number(process.argv[2])));"
    return subprocess.check_output(["node", "-e", script, text, str(width)], text=True)


def _run_export(strict: bool = False):
    if OUT.exists():
        OUT.unlink()
    env = os.environ.copy()
    if strict:
        env["SF_AUDIT_STRICT"] = "1"
    else:
        env.pop("SF_AUDIT_STRICT", None)
    subprocess.run(["/app/ops/sfdesk"], check=True, cwd="/app", env=env)
    with OUT.open() as handle:
        return json.load(handle)


def _read_events(run_id):
    with (SETS / f"{run_id}.switchlog").open(newline="") as handle:
        return list(csv.DictReader(handle))


def _expected_for(run_id):
    ctx = Namespace(
        active=None,
        rows=[],
        totals={},
        x3={},
        x4={},
        x5={},
        jackpot_count=0,
        saved_drains=0,
        tilt_balls=0,
    )

    def close_row(event):
        cur = ctx.active
        if cur is None:
            return
        saved = event["event"] == "DRAIN" and int(event["ts"]) - cur.launch_ts <= 12 and not cur.x10
        if saved:
            ctx.saved_drains += 1
            return
        lock_count = ctx.x3.get(cur.player, 0)
        bonus = 0 if cur.x10 else len(cur.x1) * 10000 + len(cur.x2) * 15000 + lock_count * 25000
        if cur.x10:
            ctx.tilt_balls += 1
        row_total = cur.base + cur.skill + cur.mode + cur.jackpot + bonus
        ctx.totals[cur.player] = ctx.totals.get(cur.player, 0) + row_total
        ctx.rows.append(
            {
                "ball": cur.ball,
                "player": cur.player,
                "base_score": cur.base,
                "skill_value": cur.skill,
                "mode_value": cur.mode,
                "jackpot_value": cur.jackpot,
                "bonus_value": bonus,
                "tilt_mark": "tilt" if cur.x10 else "clean",
                "saved_drain": 0,
                "row_total": row_total,
            }
        )
        ctx.active = None

    for event in _read_events(run_id):
        event["ball"] = int(event["ball"])
        if event["event"] == "LAUNCH":
            ctx.active = Namespace(
                ball=event["ball"],
                player=event["player"],
                launch_ts=int(event["ts"]),
                multiplier=1,
                x1=set(),
                x2=set(),
                x8=False,
                x9=0,
                x10=False,
                base=0,
                skill=0,
                mode=0,
                jackpot=0,
            )
            continue
        cur = ctx.active
        if cur is None:
            continue
        if event["event"] == "TILT_WARN":
            cur.x9 += 1
            if cur.x9 >= 2:
                cur.x10 = True
            continue
        if event["event"] == "DRAIN":
            close_row(event)
            continue
        if cur.x10:
            continue
        value = event["value"]
        if event["event"] == "MULT":
            cur.multiplier = max(1, min(3, int(value)))
        elif event["event"] == "BUMPER":
            cur.base += 1000 * int(value)
        elif event["event"] == "SPINNER":
            cur.base += 3000 * int(value) * cur.multiplier
        elif event["event"] == "LANE":
            if value in cur.x1:
                cur.skill += 5000
            else:
                cur.skill += [20000, 40000, 80000][min(len(cur.x1), 2)]
                cur.x1.add(value)
        elif event["event"] == "MODE_START":
            cur.x8 = True
            cur.x2 = set()
        elif event["event"] == "TARGET":
            if not cur.x8:
                cur.mode += 25000
            elif value in cur.x2:
                cur.mode += 10000
            else:
                cur.x2.add(value)
                cur.mode += 75000 * cur.multiplier
                if len(cur.x2) >= 4:
                    cur.x8 = False
                    cur.mode += 300000
        elif event["event"] == "LOCK":
            ctx.x3[cur.player] = min(2, ctx.x3.get(cur.player, 0) + 1)
            cur.base += 50000
            if ctx.x3[cur.player] >= 2:
                ctx.x4[cur.player] = True
                ctx.x5[cur.player] = True
        elif event["event"] == "SIDEWALL":
            if ctx.x4.get(cur.player, False):
                ctx.x5[cur.player] = True
        elif event["event"] == "JACKPOT" and ctx.x4.get(cur.player, False) and ctx.x5.get(cur.player, False):
            cur.jackpot += 500000 * cur.multiplier
            ctx.jackpot_count += 1
            ctx.x5[cur.player] = False

    for row in ctx.rows:
        material = "|".join(
            str(row[key])
            for key in [
                "ball",
                "player",
                "base_score",
                "skill_value",
                "mode_value",
                "jackpot_value",
                "bonus_value",
                "tilt_mark",
                "saved_drain",
                "row_total",
            ]
        )
        row["row_digest"] = _digest(f"{run_id}|{material}", 16)
    run_digest = _digest(":".join(row["row_digest"] for row in ctx.rows), 20)
    final_order = sorted(ctx.totals, key=lambda p: (-ctx.totals[p], p))
    return {
        "id": run_id,
        "rows": ctx.rows,
        "player_totals": ctx.totals,
        "final_order": final_order,
        "jackpot_count": ctx.jackpot_count,
        "saved_drains": ctx.saved_drains,
        "tilt_balls": ctx.tilt_balls,
        "run_digest": run_digest,
    }


def _expected_report(strict: bool = False):
    ids = [line.strip() for line in IDS.read_text().splitlines() if line.strip()]
    runs = [_expected_for(run_id) for run_id in ids]
    ordered = sorted(runs, key=lambda row: row["id"])
    return {
        "table": "constellation-kiosk",
        "runs": runs,
        "rollup": {
            "run_count": len(runs),
            "total_jackpots": sum(row["jackpot_count"] for row in runs),
            "saved_drains": sum(row["saved_drains"] for row in runs),
            "tilt_balls": sum(row["tilt_balls"] for row in runs),
            "chain_digest": _digest(":".join(row["run_digest"] for row in ordered), 24),
            "audit_latch": "sealed" if strict else "open",
        },
    }


def _by_id(report, run_id):
    return next(row for row in report["runs"] if row["id"] == run_id)


def test_cabinet_ranking_schema_and_player_order():
    """The regenerated report has the public structure and deterministic run order."""
    report = _run_export()
    expected = _expected_report()
    assert report["table"] == expected["table"]
    assert [row["id"] for row in report["runs"]] == [row["id"] for row in expected["runs"]]
    assert set(report["rollup"]) == {"run_count", "total_jackpots", "saved_drains", "tilt_balls", "chain_digest", "audit_latch"}
    for run in report["runs"]:
        expected_run = _by_id(expected, run["id"])
        assert set(run) == {"id", "rows", "player_totals", "final_order", "jackpot_count", "saved_drains", "tilt_balls", "run_digest"}
        assert run["final_order"] == expected_run["final_order"]


def test_scorecard_ranking_totals_match_cabinet_referee():
    """Every run total and closed-ball row matches an independent event run."""
    report = _run_export()
    expected = _expected_report()
    assert report["runs"] == expected["runs"]


def test_lane_scorecard_ranking_resets_per_ball():
    """Lane progress resets by ball and repeated letters score as repeats."""
    report = _run_export()
    expected = _expected_report()
    zenith = _by_id(report, "zenith")
    expected_zenith = _by_id(expected, "zenith")
    rows = {row["ball"]: row for row in zenith["rows"]}
    expected_rows = {row["ball"]: row for row in expected_zenith["rows"]}
    assert rows[2]["skill_value"] == expected_rows[2]["skill_value"]
    assert rows[3]["skill_value"] == expected_rows[3]["skill_value"]
    assert zenith["player_totals"]["A"] == expected_zenith["player_totals"]["A"]


def test_saved_drain_ranking_keeps_ball_alive():
    """A protected early drain keeps the same ball open and only increments the run counter."""
    report = _run_export()
    expected = _expected_report()
    aurora = _by_id(report, "aurora")
    expected_aurora = _by_id(expected, "aurora")
    assert aurora["saved_drains"] == expected_aurora["saved_drains"]
    assert [row["ball"] for row in aurora["rows"]] == [row["ball"] for row in expected_aurora["rows"]]
    assert aurora["rows"][0]["skill_value"] == expected_aurora["rows"][0]["skill_value"]


def test_tilt_warning_ranking_suppresses_late_scores():
    """After the second warning, later scoring switches on that ball are ignored and bonus is zero."""
    report = _run_export()
    zenith = _by_id(report, "zenith")
    tilted = zenith["rows"][0]
    assert tilted["tilt_mark"] == "tilt"
    assert tilted["bonus_value"] == 0
    assert tilted["base_score"] == 4000
    assert tilted["jackpot_value"] == 0


def test_mode_ranking_closes_distinct_target_banks():
    """Mode scoring distinguishes repeated targets and adds the close award once."""
    report = _run_export()
    aurora = _by_id(report, "aurora")
    meteor = _by_id(report, "meteor")
    assert aurora["rows"][0]["mode_value"] == 910000
    assert meteor["rows"][1]["mode_value"] == 600000


def test_jackpot_ranking_requires_lit_multiball():
    """Major awards only score while multiball is active and the award lamp is lit."""
    report = _run_export()
    expected = _expected_report()
    meteor = _by_id(report, "meteor")
    eclipse = _by_id(report, "eclipse")
    expected_meteor = _by_id(expected, "meteor")
    expected_eclipse = _by_id(expected, "eclipse")
    assert meteor["rows"][1]["jackpot_value"] == expected_meteor["rows"][1]["jackpot_value"]
    assert meteor["jackpot_count"] == expected_meteor["jackpot_count"]
    assert eclipse["rows"][1]["jackpot_value"] == expected_eclipse["rows"][1]["jackpot_value"]
    assert eclipse["jackpot_count"] == expected_eclipse["jackpot_count"]


def test_rollup_ranking_counts_match_score_rows():
    """Rollup counters are derived from run records, not from stale machine state."""
    report = _run_export()
    assert report["rollup"]["run_count"] == len(report["runs"])
    assert report["rollup"]["total_jackpots"] == sum(row["jackpot_count"] for row in report["runs"])
    assert report["rollup"]["saved_drains"] == sum(row["saved_drains"] for row in report["runs"])
    assert report["rollup"]["tilt_balls"] == sum(row["tilt_balls"] for row in report["runs"])


def test_sha256_row_folding_recomputes_chain_digest():
    """Row, run and chain digests are reproducible from the visible report fields."""
    report = _run_export()
    expected = _expected_report()
    assert [(r["id"], r["run_digest"]) for r in report["runs"]] == [(r["id"], r["run_digest"]) for r in expected["runs"]]
    assert report["rollup"]["chain_digest"] == expected["rollup"]["chain_digest"]
    again = _run_export()
    assert again["rollup"]["chain_digest"] == report["rollup"]["chain_digest"]


def test_strict_latch_preserves_cabinet_scores():
    """Strict audit mode changes only the rollup latch and leaves scoring artifacts stable."""
    normal = _run_export(strict=False)
    strict = _run_export(strict=True)
    assert normal["rollup"]["audit_latch"] == "open"
    assert strict["rollup"]["audit_latch"] == "sealed"
    normal_rollup = {k: v for k, v in normal["rollup"].items() if k != "audit_latch"}
    strict_rollup = {k: v for k, v in strict["rollup"].items() if k != "audit_latch"}
    assert strict_rollup == normal_rollup
    assert strict["runs"] == normal["runs"]
