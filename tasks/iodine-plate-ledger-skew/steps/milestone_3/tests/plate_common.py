"""Shared verifier helpers for iodine plate ledger replay."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

APP = Path("/app")
BIN_PATH = "/app/target/release/iodine-plate"
SUBCMD = "plate"
FLAG = "--ledger"
SCEN_DIR = APP / "fixtures" / "scenarios"
SEG_ROOT = APP / "fixtures" / "segments"
PROFILE_DIR = APP / "profiles"
OUT = Path("/app/output/iodine_plate_report.json")
TRACE = Path("/app/output/iodine_plate_trace.tsv")
CACHE_HEAD = APP / "var" / "cache" / "head"
CACHE_GEN = APP / "var" / "cache" / "gen"
REBUILD = Path(__file__).resolve().parent / "rebuild_release.sh"
LANE_MASK_OPEN = 65535


def _le_u32(raw: bytes, offset: int) -> int:
    return (
        raw[offset]
        | (raw[offset + 1] << 8)
        | (raw[offset + 2] << 16)
        | (raw[offset + 3] << 24)
    )


def _le_u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def _digest32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def _digest_start(anchor: int) -> int:
    return 6 if anchor == 1 else 8


def _parse_profile_fields(name: str | None) -> dict:
    out = {"digest_anchor": 0, "lane_mask": LANE_MASK_OPEN}
    if not name:
        return out
    raw = (PROFILE_DIR / f"{name}.toml").read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "digest_anchor":
            out["digest_anchor"] = int(value)
        elif key == "lane_mask":
            out["lane_mask"] = int(value)
    return out


def _read_row_plt5(path: Path, digest_anchor: int) -> dict:
    raw = path.read_bytes()
    if len(raw) < 24 or raw[0:4] != b"PLT5":
        return {"name": path.name, "plate_lane": 0, "seq": 0, "digest_match": False}
    plate_lane = _le_u16(raw, 6)
    seq = _le_u32(raw, 12)
    length = _le_u32(raw, 16)
    end = 20 + length
    if len(raw) < end + 4:
        return {"name": path.name, "plate_lane": 0, "seq": 0, "digest_match": False}
    span_start = _digest_start(digest_anchor)
    body = raw[span_start:end]
    tail = raw[end : end + 4]
    digest_ok = _le_u32(tail, 0) == _digest32(body)
    return {
        "name": path.name,
        "plate_lane": plate_lane,
        "seq": seq,
        "digest_match": digest_ok,
    }


def _parse_trim_sequence(raw: str) -> list[str]:
    start = raw.find("[")
    if start < 0:
        return []
    end = raw.find("]", start)
    if end < 0:
        return []
    return [
        part.strip().strip('"')
        for part in raw[start + 1 : end].split(",")
        if part.strip().strip('"') in {"rollback_after", "prune_below"}
    ]


def _parse_modulo_prune(raw: str) -> int | None:
    for line in raw.splitlines():
        parts = line.split("=")
        if len(parts) == 2 and parts[0].strip() == "modulo_prune":
            try:
                return int(parts[1].strip())
            except ValueError:
                pass
    return None


def _get_dynamic_stamp(records_applied: int) -> str:
    salt_path = APP / "policy" / "cache_salt.txt"
    if not salt_path.is_file():
        return ""
    salt = int(salt_path.read_text(encoding="utf-8").strip())
    product = salt * records_applied
    return str(_digest32(str(product).encode("utf-8")))


def _trim_sequence(meta: dict) -> list[str]:
    profile = meta.get("profile")
    if profile:
        profile_path = PROFILE_DIR / f"{profile}.toml"
        return _parse_trim_sequence(profile_path.read_text(encoding="utf-8"))
    if meta.get("rollback_after") is not None:
        return ["rollback_after"]
    if meta.get("prune_below") is not None:
        return ["prune_below"]
    return []


def _lane_mask_allows(lane: int, lane_mask: int) -> bool:
    if lane_mask == LANE_MASK_OPEN:
        return True
    return ((lane_mask >> lane) & 1) == 1


def _apply_gate_filters(rows: list[dict], meta: dict, profile_fields: dict) -> list[dict]:
    kept = list(rows)
    expect_lane = meta.get("plate_lane")
    if expect_lane is not None:
        kept = [row for row in kept if row["plate_lane"] == expect_lane]
    lane_mask = profile_fields["lane_mask"]
    if lane_mask != LANE_MASK_OPEN:
        kept = [row for row in kept if _lane_mask_allows(row["plate_lane"], lane_mask)]
    kept.sort(key=lambda row: row["seq"])
    return kept


def _apply_trim_steps(rows: list[dict], meta: dict) -> list[dict]:
    kept = list(rows)
    for step in _trim_sequence(meta):
        if step == "rollback_after" and meta.get("rollback_after") is not None:
            marker = meta["rollback_after"]
            kept = [row for row in kept if row["seq"] <= marker]
        elif step == "prune_below" and meta.get("prune_below") is not None:
            marker = meta["prune_below"]
            kept = [row for row in kept if row["seq"] >= marker]

    profile = meta.get("profile")
    if profile:
        profile_path = PROFILE_DIR / f"{profile}.toml"
        if profile_path.is_file():
            modulo = _parse_modulo_prune(profile_path.read_text(encoding="utf-8"))
            if modulo is not None:
                kept = [row for row in kept if row["seq"] % modulo != 0]

    modulo = meta.get("modulo_prune")
    if modulo is not None:
        kept = [row for row in kept if row["seq"] % modulo != 0]

    return kept


def _get_pre_trim(scenario: str) -> list[dict]:
    meta = json.loads((SCEN_DIR / f"{scenario}.json").read_text(encoding="utf-8"))
    profile_fields = _parse_profile_fields(meta.get("profile"))
    seg_dir = SEG_ROOT / scenario
    rows = [
        _read_row_plt5(seg_dir / name, profile_fields["digest_anchor"])
        for name in meta["segments"]
    ]
    return _apply_gate_filters(rows, meta, profile_fields)


def expected_for(scenario: str) -> dict:
    meta = json.loads((SCEN_DIR / f"{scenario}.json").read_text(encoding="utf-8"))
    pre_gate = [
        _read_row_plt5(
            (SEG_ROOT / scenario) / name,
            _parse_profile_fields(meta.get("profile"))["digest_anchor"],
        )
        for name in meta["segments"]
    ]
    profile_fields = _parse_profile_fields(meta.get("profile"))
    gated = _apply_gate_filters(pre_gate, meta, profile_fields)
    rows = _apply_trim_steps(gated, meta)
    applied = sum(1 for row in rows if row["digest_match"])
    head = max((row["seq"] for row in rows), default=0)
    if not rows:
        chain = "empty"
    elif applied == len(rows):
        chain = "valid"
    else:
        chain = "broken"
    return {
        "scenario": scenario,
        "head_seq": head,
        "records_applied": applied,
        "digest_chain": chain,
        "segments": [
            {"name": row["name"], "seq": row["seq"], "digest_match": row["digest_match"]}
            for row in rows
        ],
    }


def expected_trace(expected: dict, pre_trim: list[dict]) -> str:
    retained = {row["name"] for row in expected["segments"]}
    lines = ["seq,plate_lane,digest_match,retained"]
    for row in pre_trim:
        digest = 1 if row["digest_match"] else 0
        kept = 1 if row["name"] in retained else 0
        lines.append(f"{row['seq']},{row['plate_lane']},{digest},{kept}")
    return "\n".join(lines) + "\n"


def build_release() -> None:
    proc = subprocess.run(
        ["bash", str(REBUILD)],
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError("cargo build failed:\n" + proc.stdout + proc.stderr)


def run_driver(scenario: str) -> dict:
    build_release()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    if TRACE.exists():
        TRACE.unlink()
    proc = subprocess.run(
        [BIN_PATH, SUBCMD, FLAG, scenario, "--output", "/app/output/iodine_plate_report.json"],
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"driver failed: {BIN_PATH} {SUBCMD} {FLAG} {scenario}\n{proc.stdout}\n{proc.stderr}"
        )
    return json.loads(OUT.read_text(encoding="utf-8"))


def read_trace() -> str:
    assert TRACE.is_file(), "trace sidecar missing"
    return TRACE.read_text(encoding="utf-8")


def clear_outputs() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    if TRACE.exists():
        TRACE.unlink()
    for cache_dir in (CACHE_HEAD, CACHE_GEN):
        if cache_dir.exists():
            for child in cache_dir.glob("*"):
                child.unlink()


def get_pre_trim(scenario: str) -> list[dict]:
    return _get_pre_trim(scenario)


def install_probe_scenario(name: str, probe_root: Path) -> None:
    assert probe_root.is_dir(), "probe fixtures missing"
    shutil.copy2(
        probe_root / "scenarios" / f"{name}.json",
        SCEN_DIR / f"{name}.json",
    )
    dest = SEG_ROOT / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(probe_root / "segments" / name, dest)
