"""DF auxiliary profile-cache replay session helpers for grading."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import zlib
from dataclasses import dataclass, field
from pathlib import Path

INVOKE = "/app/environment/tools/r8_run"
Z2 = "/app/environment/tools/r8_emit"
RECOVER = "/app/environment/tools/r8_recover"
OUT = Path("/app/output/r8_trace.json")
SEQ_ROOT = Path("/app/cases/seq")
STATE = Path("/app/replay-state")
STORE = STATE / "store"
WRITE_BUMP = 1
WAL_TAB = "\t"
VIEWS = ("reduce", "promote", "live")
RUN_TIMEOUT = 300
MIN_CHAIN_ROWS = 18
MIN_WAL_LINES = 25


@dataclass
class R8ReplaySession:
    """Drive m6 replay tools and read artifacts."""

    timeout: int = RUN_TIMEOUT

    def wipe(self) -> None:
        if OUT.exists():
            OUT.unlink()
        if STATE.exists():
            shutil.rmtree(STATE)
        STATE.mkdir(parents=True, exist_ok=True)
        for sub in ("store", "live", "promote", "wal"):
            (STATE / sub).mkdir(exist_ok=True)

    def invoke(self, scenario: int) -> None:
        subprocess.run(
            [INVOKE, "--scenario", str(scenario)],
            check=True,
            timeout=self.timeout,
        )
        cache = STATE / f"epoch_{scenario}.json"
        assert len(json.loads(cache.read_text(encoding="utf-8"))) >= 1

    def invoke_range(self, start: int, end: int) -> None:
        for n in range(start, end + 1):
            self.invoke(n)

    def emit(self) -> None:
        subprocess.run(
            [Z2, "--out", str(OUT)],
            check=True,
            timeout=self.timeout,
        )

    def recover(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [RECOVER],
            check=False,
            timeout=self.timeout,
            text=True,
        )

    def emit_allow_fail(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [Z2, "--out", str(OUT)],
            check=False,
            timeout=self.timeout,
            text=True,
        )

    def chain_through(self, scenario: int, *, emit: bool = False) -> None:
        self.wipe()
        self.invoke_range(0, scenario)
        if emit:
            self.emit()

    def report(self) -> dict:
        return json.loads(OUT.read_text(encoding="utf-8"))

    def wal_lines(self) -> list[dict]:
        wal_path = STATE / "wal" / "chain.wal"
        records: list[dict] = []
        for line in wal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            body, crc_str = line.split(WAL_TAB, 1)
            rec = json.loads(body)
            payload = (
                f"{rec['scenario']}:{rec['phase']}:{rec['feed_gen']}:"
                f"{rec['live_gen']}:{rec['seq']}"
            )
            assert int(crc_str) == wal_crc(payload)
            records.append(rec)
        return records

    def rows(self, report: dict, scenario: int, view: str) -> list[dict]:
        return [r for r in report["epochs"] if r["scenario"] == scenario and r["view"] == view]

    def checkpoint(self) -> dict:
        return json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))

    def epoch_rows(self, scenario: int) -> list[dict]:
        return json.loads((STATE / f"epoch_{scenario}.json").read_text(encoding="utf-8"))

def wal_crc(payload: str) -> int:
    return zlib.crc32(payload.encode("utf-8")) & 0xFFFFFFFF


def row_digest(rows: list[dict]) -> str:
    from band_ref import body_digest

    return body_digest(rows)


def t9_narrow_ok(observed: float, generation: int, action_code: int) -> bool:
    from band_ref import t9_narrow_ok as _ok

    return _ok(observed, generation, action_code)


def parse_arr(path: Path) -> dict[str, dict[str, int | str]]:
    slots: dict[str, dict[str, int | str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts: dict[str, str] = {}
        name = ""
        for item in line.split():
            if "=" not in item:
                continue
            key, _, val = item.partition("=")
            if key == "slot":
                name = val.strip()
            else:
                parts[key] = val
        if not name:
            continue
        slots[name] = dict(
            principal=parts.get("principal", "svc1"),
            label=parts.get("label", "ROOT"),
            gen=int(parts["gen"]),
            action=int(parts.get("action", 0)),
        )
    return slots


def parse_tab(path: Path) -> tuple[int, str]:
    epoch = 1
    digest = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for item in line.split():
            if "=" not in item:
                continue
            key, _, val = item.partition("=")
            if key == "epoch":
                epoch = int(val)
            elif key == "digest":
                digest = val
    return epoch, digest


def shipped_gen(scenario: int) -> int:
    return int(parse_arr(SEQ_ROOT / f"s{scenario}/a0.arr")["active"]["gen"]) + WRITE_BUMP


def scenario_include_tab(scenario: int) -> Path:
    """Abstraction include snapshot for one scenario fixture tree (driver_notes.md)."""
    path = SEQ_ROOT / f"s{scenario}" / "i0.tab"
    assert path.is_file(), f"missing include snapshot for scenario {scenario}"
    return path


def scenario_metrics_epoch(scenario: int) -> int:
    epoch, _digest = parse_tab(scenario_include_tab(scenario))
    return epoch


def primary_row(rows: list[dict]) -> dict:
    assert rows
    return rows[0]


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda r: (r["scenario"], r["view"], r["principal"], r["label"], r["generation"]),
    )


def bust_before_success(records: list[dict], scenario: int) -> None:
    phases = [rec["phase"] for rec in records if rec["scenario"] == scenario]
    if scenario == 0 or not phases:
        return
    assert phases[0] == "bust"
    assert "success" in phases
    assert phases.index("success") > phases.index("bust")


def order_seal_from_wal(chain: list[dict]) -> int:
    seal = 0
    last_scenario = 0xFFFFFFFF
    saw_bust = False
    for rec in chain:
        sc = int(rec["scenario"])
        if sc != last_scenario:
            last_scenario = sc
            saw_bust = False
        phase = rec["phase"]
        if phase == "bust":
            saw_bust = True
        if phase == "success" and saw_bust:
            seal = (seal + 0xBEEF) & 0xFFFFFFFFFFFFFFFF
        if phase == "success" and not saw_bust:
            seal = ((seal * 31) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
        if phase == "bust" and not saw_bust:
            seal = ((seal * 37) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
    return seal


def lineage_seal_from_wal(chain: list[dict]) -> int:
    sync_tail: dict[int, dict] = {}
    for rec in chain:
        if rec["phase"] == "sync":
            sync_tail[int(rec["scenario"])] = rec
    seal = 0
    for scenario in sorted(sync_tail):
        rec = sync_tail[scenario]
        live = int(rec["live_gen"])
        seal = (
            (seal * 131)
            + (scenario << 24)
            + (int(rec["feed_gen"]) << 12)
            + live
        ) & 0xFFFFFFFFFFFFFFFF
    return seal


def broken_order_seal(chain: list[dict]) -> int:
    seal = 0
    last_scenario = 0xFFFFFFFF
    saw_bust = False
    for rec in chain:
        sc = int(rec["scenario"])
        if sc != last_scenario:
            last_scenario = sc
            saw_bust = False
        phase = rec["phase"]
        if phase == "bust":
            saw_bust = True
        if phase == "success" and saw_bust:
            seal = ((seal * 31) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
        if phase == "success" and not saw_bust:
            seal = ((seal * 31) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
        if phase == "bust" and not saw_bust:
            seal = ((seal * 37) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
    return seal


@dataclass
class ReportContract:
    """Session wrapper for verifier helpers."""

    session: R8ReplaySession = field(default_factory=R8ReplaySession)


def verify_row_schema(report: dict) -> None:
    assert "epochs" in report
    assert "body_digest" in report
    for row in report["epochs"]:
        for key in (
            "scenario",
            "view",
            "principal",
            "label",
            "generation",
            "action_code",
            "block_rms",
        ):
            assert key in row
        assert row["view"] in VIEWS


def verify_row_digest(report: dict) -> None:
    assert report["body_digest"] == row_digest(report["epochs"])


def verify_s0_generations(session: R8ReplaySession, report: dict) -> None:
    expected = shipped_gen(0)
    for view in VIEWS:
        row = primary_row(session.rows(report, 0, view))
        assert row["generation"] == expected


def verify_scenarios_present(session: R8ReplaySession, report: dict, max_scenario: int) -> None:
    for n in range(max_scenario + 1):
        for view in VIEWS:
            assert session.rows(report, n, view)


def verify_cross_view_policy(session: R8ReplaySession, report: dict, max_scenario: int = 4) -> None:
    for n in range(1, max_scenario + 1):
        reduce_rows = session.rows(report, n, "reduce")
        live_rows = session.rows(report, n, "live")
        promote_rows = session.rows(report, n, "promote")
        assert reduce_rows and live_rows and promote_rows
        reduce = primary_row(reduce_rows)
        live = primary_row(live_rows)
        if n == 3 and any(r.get("action_code") == 9 for r in live_rows):
            continue
        assert reduce["generation"] == live["generation"]
        catalog_gen = max(r["generation"] for r in promote_rows)
        if live["generation"] > catalog_gen:
            assert any(r.get("action_code", 0) != 0 for r in live_rows)


def verify_transition_rows(session: R8ReplaySession, report: dict) -> None:
    assert len(session.rows(report, 2, "live")) >= 2
    assert len(session.rows(report, 3, "live")) >= 2
    assert len(session.rows(report, 4, "live")) >= 2
    assert any(r.get("action_code") == 9 for r in session.rows(report, 3, "live"))
    assert any(r.get("action_code") == 6 for r in session.rows(report, 4, "live"))
    s2_live = session.rows(report, 2, "live")
    assert any(r.get("action_code", 0) != 0 for r in s2_live[1:])


def verify_checkpoint_seals(session: R8ReplaySession) -> None:
    records = session.wal_lines()
    cp = session.checkpoint()
    assert cp.get("valid") is True
    assert cp.get("order_seal") == order_seal_from_wal(records)
    assert int(cp.get("lineage_seal", -1)) == lineage_seal_from_wal(records)


def verify_digest_slot_keys() -> None:
    slot_files = list(STORE.glob("*.slot"))
    assert slot_files
    joined = " ".join(p.name for p in slot_files)
    _epoch, digest = parse_tab(scenario_include_tab(1))
    assert digest
    assert digest in joined


def verify_metrics_epoch(min_epoch: int) -> None:
    metrics_path = STATE / "last_metrics.json"
    assert metrics_path.is_file()
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert int(metrics.get("crl_epoch", 0)) >= min_epoch


def verify_epoch_transition_cache(session: R8ReplaySession, scenario: int) -> None:
    rows = session.epoch_rows(scenario)
    live_rows = [r for r in rows if r.get("view") == "live"]
    assert len(live_rows) >= 2
    assert any(int(r.get("action_code", 0)) != 0 for r in live_rows)


def verify_seq_no_reset(records: list[dict]) -> None:
    by_scenario: dict[int, list[int]] = {}
    for rec in records:
        by_scenario.setdefault(int(rec["scenario"]), []).append(int(rec["seq"]))
    for scenario in range(2, 5):
        if scenario not in by_scenario or scenario - 1 not in by_scenario:
            continue
        assert min(by_scenario[scenario]) > max(by_scenario[scenario - 1])


def verify_order_seal_bust_mixing(records: list[dict]) -> None:
    """order_seal must use bust-then-success mixing documented in r8_contract.md."""
    assert order_seal_from_wal(records) != broken_order_seal(records)
    for scenario in range(1, 5):
        phases = [rec["phase"] for rec in records if int(rec["scenario"]) == scenario]
        if "bust" in phases and "success" in phases:
            assert phases.index("bust") < phases.index("success")


def verify_t9_narrow_rows(rows: list[dict]) -> None:
    for row in rows:
        view = row.get("view")
        if view not in ("reduce", "promote"):
            continue
        gen = int(row["generation"])
        act = int(row.get("action_code", 0))
        assert t9_narrow_ok(float(row["block_rms"]), gen, act)


def verify_r8_narrow_report(
    session: R8ReplaySession, report: dict, *, through_scenario: int
) -> None:
    for scenario in range(through_scenario + 1):
        for view in ("reduce", "promote"):
            verify_t9_narrow_rows(session.rows(report, scenario, view))


def cargo_rebuild() -> None:
    subprocess.run(
        ["cargo", "build", "--release", "--locked"],
        cwd="/app/environment",
        check=True,
        timeout=900,
        env=os.environ,
    )


def run_chain(session: R8ReplaySession, scenario: int, *, emit: bool = False) -> None:
    session.chain_through(scenario, emit=emit)


def run_invoke(session: R8ReplaySession, scenario: int) -> None:
    session.invoke(scenario)


def run_emit(session: R8ReplaySession) -> None:
    session.emit()


def load_report(session: R8ReplaySession) -> dict:
    return session.report()


def load_wal(session: R8ReplaySession) -> list[dict]:
    return session.wal_lines()


def load_epoch(session: R8ReplaySession, scenario: int) -> list[dict]:
    return session.epoch_rows(scenario)


def load_checkpoint(session: R8ReplaySession) -> dict:
    return session.checkpoint()


def run_recover(session: R8ReplaySession) -> int:
    return session.recover().returncode


def run_emit_allow_fail(session: R8ReplaySession) -> int:
    return session.emit_allow_fail().returncode


def wipe_workspace(session: R8ReplaySession) -> None:
    session.wipe()


def rows_for(session: R8ReplaySession, report: dict, scenario: int, view: str) -> list[dict]:
    return session.rows(report, scenario, view)


