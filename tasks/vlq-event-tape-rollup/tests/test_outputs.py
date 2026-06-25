import json
import shutil
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
RUN_OUTPUT = "/app/output/vlt_report.json"
OUT = Path(RUN_OUTPUT)
BIND_MANIFEST = "/app/environment/fixtures/z7bind.json"
REF = Path(__file__).resolve().parent / "ref_caps"
REF_MANIFEST = REF / "z7bind.json"
FIXTURE_ROOT = REF
JOURNAL = APP / "var" / "vlt_journal"
PANEL_ORDER = ["t2", "t5", "t8"]
SEED = 1469598103934665603
STEP = 1099511628211
MASK = (1 << 64) - 1
BUILT = False


def _digest_bytes(data: bytes) -> str:
    h = SEED
    for b in data:
        h ^= b
        h = (h * STEP) & MASK
    return f"{h:016x}"


def _digest(text: str) -> str:
    return _digest_bytes(text.encode())


def _vlq_u(data: bytes, offset: int) -> tuple[int, int]:
    acc = 0
    shift = 0
    while offset < len(data):
        b = data[offset]
        offset += 1
        acc |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            break
    return acc, offset


def _vlq_s(data: bytes, offset: int) -> tuple[int, int]:
    u, offset = _vlq_u(data, offset)
    val = (u >> 1) ^ (-(u & 1))
    return val, offset


def _u16le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def _u32le(data: bytes, offset: int) -> int:
    return (
        data[offset]
        | (data[offset + 1] << 8)
        | (data[offset + 2] << 16)
        | (data[offset + 3] << 24)
    )


def _read_vlt1(path: Path) -> tuple[list[tuple[int, int]], str]:
    data = path.read_bytes()
    assert data[:4] == b"VLT1"
    count = _u32le(data, 6)
    offset = 10
    events: list[tuple[int, int]] = []
    for _ in range(count):
        tag, offset = _vlq_u(data, offset)
        delta, offset = _vlq_s(data, offset)
        plen = _u16le(data, offset)
        offset += 2 + plen
        events.append((tag, delta))
    return events, _digest_bytes(data)


def _fold_ref(events: list[tuple[int, int]], start: int, end: int) -> int:
    return sum(d for _, d in events[start:end])


def _peek_ref(events: list[tuple[int, int]], at: int) -> int:
    return events[at][1]


def _tally_ref(events: list[tuple[int, int]], mask: int) -> int:
    return sum(1 for tag, _ in events if (tag & mask) != 0)


def _tag_span_ref(events: list[tuple[int, int]]) -> int:
    return max((tag for tag, _ in events), default=0)


def _row_serial(panel: dict) -> str:
    parts = [panel["name"], str(panel["event_count"]), str(panel["tag_span"])]
    for cell in panel["answers"]:
        if cell["op"] == "fold":
            parts.extend(["fold", str(cell["from"]), str(cell["to"]), str(cell["value"])])
        elif cell["op"] == "peek":
            parts.extend(["peek", str(cell["at"]), str(cell["value"])])
        else:
            parts.extend(["tally", str(cell["mask"]), str(cell["value"])])
    return "|".join(parts)


def _checkpoint_body(panel: dict, tape_fp: str) -> str:
    return f"{panel['name']}|{tape_fp}|{panel['row_digest']}"


def _tail_binding_from_panels(panels: list[dict], tape_fps: dict[str, str]) -> str:
    parts = []
    for panel in panels:
        name = panel["name"]
        raw = _checkpoint_body(panel, tape_fps[name])
        parts.append(f"{name}.chk={_digest(raw)}")
    return _digest("\n".join(parts))


def _compute_expected(*, use_disk_journal: bool = False) -> tuple[dict, dict[str, str]]:
    manifest = json.loads(REF_MANIFEST.read_text(encoding="utf-8"))
    panels = []
    tape_fps: dict[str, str] = {}
    for entry in manifest["panels"]:
        events, tape_fp = _read_vlt1(FIXTURE_ROOT / entry["bundle"])
        tape_fps[entry["name"]] = tape_fp
        answers = []
        for q in entry["queries"]:
            if q["op"] == "fold":
                val = _fold_ref(events, q["from"], q["to"])
                answers.append({"op": "fold", "from": q["from"], "to": q["to"], "value": val})
            elif q["op"] == "peek":
                val = _peek_ref(events, q["at"])
                answers.append({"op": "peek", "at": q["at"], "value": val})
            else:
                val = _tally_ref(events, q["mask"])
                answers.append({"op": "tally", "mask": q["mask"], "value": val})
        panel = {
            "name": entry["name"],
            "event_count": len(events),
            "tag_span": _tag_span_ref(events),
            "answers": answers,
        }
        panel["row_digest"] = _digest(_row_serial(panel))
        panels.append(panel)
    top_body = f"{manifest['schema_version']}|{manifest['campaign_id']}\n" + "\n".join(
        _row_serial(p) for p in panels
    )
    if use_disk_journal:
        tail_parts = []
        for name in PANEL_ORDER:
            raw = (JOURNAL / f"{name}.chk").read_bytes()
            tail_parts.append(f"{name}.chk={_digest_bytes(raw)}")
        tail_binding = _digest("\n".join(tail_parts))
    else:
        tail_binding = _tail_binding_from_panels(panels, tape_fps)
    return {
        "schema_version": manifest["schema_version"],
        "campaign_id": manifest["campaign_id"],
        "panels": panels,
        "digest": _digest(top_body + "\n" + tail_binding),
    }, tape_fps


def _build() -> None:
    global BUILT
    if BUILT:
        return
    subprocess.run(
        ["cmake", "-S", "/app/environment", "-B", "/app/build", "-G", "Ninja"],
        check=True,
        cwd=APP,
    )
    subprocess.run(["ninja", "-C", "/app/build"], check=True, cwd=APP)
    BUILT = True


def _clear_journal() -> None:
    if JOURNAL.exists():
        shutil.rmtree(JOURNAL)
    JOURNAL.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _warm() -> None:
    _build()


def _run(*extra_flags: str) -> dict:
    _build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    cmd = ["/app/build/vlt_run", BIND_MANIFEST, RUN_OUTPUT, *extra_flags]
    subprocess.run(cmd, check=True, cwd=APP)
    return json.loads(OUT.read_text(encoding="utf-8"))


def test_vlt_journal_tail_binding() -> None:
    """Cold run binds campaign digest to on-disk journal checkpoint tail."""
    _clear_journal()
    doc = _run("--reset")
    exp, _ = _compute_expected(use_disk_journal=True)
    assert doc["schema_version"] == exp["schema_version"]
    assert doc["campaign_id"] == exp["campaign_id"]
    assert doc["digest"] == exp["digest"]
    for name in PANEL_ORDER:
        chk = JOURNAL / f"{name}.chk"
        assert chk.is_file(), f"missing checkpoint {chk}"


def test_v01_t2_answers() -> None:
    """t2 fold peek and tally answers match fixture-derived values."""
    _clear_journal()
    doc = _run("--reset")
    exp, _ = _compute_expected()
    panel = next(p for p in doc["panels"] if p["name"] == "t2")
    exp_panel = next(p for p in exp["panels"] if p["name"] == "t2")
    assert panel == exp_panel


def test_v02_t5_answers() -> None:
    """t5 fold peek and tally answers match fixture-derived values."""
    _clear_journal()
    doc = _run("--reset")
    exp, _ = _compute_expected()
    panel = next(p for p in doc["panels"] if p["name"] == "t5")
    exp_panel = next(p for p in exp["panels"] if p["name"] == "t5")
    assert panel == exp_panel


def test_v03_t8_answers() -> None:
    """t8 fold peek and tally answers match fixture-derived values."""
    _clear_journal()
    doc = _run("--reset")
    exp, _ = _compute_expected()
    panel = next(p for p in doc["panels"] if p["name"] == "t8")
    exp_panel = next(p for p in exp["panels"] if p["name"] == "t8")
    assert panel == exp_panel


def test_vlt_checkpoint_manifest_order() -> None:
    """Journal checkpoints are written in manifest panel order with bound preimages."""
    _clear_journal()
    _run("--reset")
    exp, tape_fps = _compute_expected()
    seen = []
    for name in PANEL_ORDER:
        chk = JOURNAL / f"{name}.chk"
        assert chk.is_file()
        seen.append(name)
        exp_panel = next(p for p in exp["panels"] if p["name"] == name)
        expected_body = _checkpoint_body(exp_panel, tape_fps[name])
        assert chk.read_text(encoding="utf-8") == expected_body
    assert seen == PANEL_ORDER


def test_v05_root_chain() -> None:
    """Root chain matches serialized header, panel rows, and journal tail."""
    _clear_journal()
    doc = _run("--reset")
    exp, _ = _compute_expected(use_disk_journal=True)
    assert doc["digest"] == exp["digest"]


def test_v06_row_chain_roundtrip() -> None:
    """Each panel row_digest matches recomputed row serialization."""
    _clear_journal()
    doc = _run("--reset")
    for panel in doc["panels"]:
        assert panel["row_digest"] == _digest(_row_serial(panel))


def test_vlt_reset_recovers_corrupt_journal() -> None:
    """Reset rebuilds checkpoints after journal corruption and restores digest."""
    _clear_journal()
    _run("--reset")
    first = OUT.read_bytes()
    (JOURNAL / "t5.chk").write_text("corrupt-bytes", encoding="utf-8")
    doc = _run("--reset")
    exp, _ = _compute_expected(use_disk_journal=True)
    second = OUT.read_bytes()
    assert doc == exp
    assert first == second


def test_v08_static_output_rejected() -> None:
    """Hand-written JSON with wrong fold totals fails answer checks."""
    _build()
    bad = {
        "schema_version": 1,
        "campaign_id": "vlt_roll_demo",
        "panels": [
            {
                "name": "t2",
                "event_count": 5,
                "tag_span": 8,
                "answers": [{"op": "fold", "from": 0, "to": 5, "value": 99}],
                "row_digest": "z" * 16,
            }
        ],
        "digest": "z" * 16,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bad), encoding="utf-8")
    _clear_journal()
    doc = _run("--reset")
    exp, _ = _compute_expected()
    panel = next(p for p in doc["panels"] if p["name"] == "t2")
    exp_panel = next(p for p in exp["panels"] if p["name"] == "t2")
    assert panel == exp_panel


def test_vlt_warm_lane_fingerprint_guard() -> None:
    """Warm replay reuses lane only when bundle fingerprints still match."""
    _clear_journal()
    cold = _run("--reset")
    checkpoints = {name: (JOURNAL / f"{name}.chk").read_bytes() for name in PANEL_ORDER}
    warm = _run("--warm")
    assert warm == cold
    for name in PANEL_ORDER:
        assert (JOURNAL / f"{name}.chk").read_bytes() == checkpoints[name]


def test_vlt_warm_lane_fingerprint_invalidation() -> None:
    """Warm replay reloads lane when on-disk bundle fingerprint no longer matches cache."""
    bundle_path = APP / "environment/fixtures/tapes/t5.vlt"
    original = bundle_path.read_bytes()
    _clear_journal()
    cold = _run("--reset")
    stale_t5_chk = (JOURNAL / "t5.chk").read_bytes()
    try:
        mutated = bytearray(original)
        mutated[-1] ^= 0x01
        bundle_path.write_bytes(mutated)
        mutated_fp = _digest_bytes(bytes(mutated))
        assert mutated_fp != _digest_bytes(original)

        warm = _run("--warm")
        fresh_t5_chk = (JOURNAL / "t5.chk").read_bytes()
        assert fresh_t5_chk != stale_t5_chk
        name, tape_fp, _row_digest = fresh_t5_chk.decode("utf-8").split("|")
        assert name == "t5"
        assert tape_fp == mutated_fp
        assert warm["digest"] != cold["digest"]
        cold_panel = next(p for p in cold["panels"] if p["name"] == "t5")
        warm_panel = next(p for p in warm["panels"] if p["name"] == "t5")
        assert warm_panel["answers"] == cold_panel["answers"]
    finally:
        bundle_path.write_bytes(original)


def test_vlt_fold_peek_lane_consistency() -> None:
    """Fold segments agree with peek samples on the same decoded delta lane."""
    _clear_journal()
    doc = _run("--reset")
    manifest = json.loads(REF_MANIFEST.read_text(encoding="utf-8"))
    for entry in manifest["panels"]:
        panel = next(p for p in doc["panels"] if p["name"] == entry["name"])
        events, _ = _read_vlt1(FIXTURE_ROOT / entry["bundle"])
        for q in entry["queries"]:
            if q["op"] != "fold":
                continue
            got = next(c for c in panel["answers"] if c["op"] == "fold" and c["from"] == q["from"] and c["to"] == q["to"])
            manual = sum(events[i][1] for i in range(q["from"], q["to"]))
            assert got["value"] == manual
        for q in entry["queries"]:
            if q["op"] != "peek":
                continue
            got = next(c for c in panel["answers"] if c["op"] == "peek" and c["at"] == q["at"])
            assert got["value"] == events[q["at"]][1]
