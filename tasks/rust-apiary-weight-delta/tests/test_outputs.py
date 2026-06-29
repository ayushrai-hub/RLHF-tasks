"""Independent verifier for hardened hive_scale replay semantics."""

from __future__ import annotations

import json
import struct
import subprocess
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

APP = Path("/app")
BIN = Path("/app/bin/hive_scale")
SRC = APP / "src"


def frame_checksum(body: bytes) -> int:
    return sum(body) & 0xFFFFFFFF


def pack_v2(
    frame_type: int,
    event_id: int,
    ts: int,
    raw_hive: int,
    grams: int,
    correction_target: int = 0,
    source_seq: int = 0,
    *,
    bad_checksum: bool = False,
    bad_magic: bool = False,
) -> bytes:
    body = bytearray(36)
    body[0:4] = b"BAD!" if bad_magic else b"HWS2"
    body[4] = 2
    body[5] = frame_type
    struct.pack_into("<H", body, 6, 0)
    struct.pack_into("<Q", body, 8, event_id)
    struct.pack_into("<Q", body, 16, ts)
    struct.pack_into("<H", body, 24, raw_hive)
    struct.pack_into("<i", body, 26, grams)
    struct.pack_into("<I", body, 30, correction_target)
    struct.pack_into("<H", body, 34, source_seq)
    chk = frame_checksum(bytes(body))
    if bad_checksum:
        chk ^= 0xDEADBEEF
    return bytes(body) + struct.pack("<I", chk)


def pack_v1(ts: int, hive: int, grams: int) -> bytes:
    body = b"HWSC" + struct.pack("<Q", ts) + bytes([hive & 0xFF]) + struct.pack("<I", grams)
    chk = sum(body) & 0xFFFFFFFF
    return body + struct.pack("<I", chk) + b"\x00\x00\x00"


V2_SIZE = 40
V1_SIZE = 24


@dataclass
class AliasEpoch:
    raw_hive_id: int
    canonical_hive_id: int
    from_ts: int
    until_ts: int | None = None


@dataclass
class TareEpoch:
    hive_id: int
    from_ts: int
    tare_kg: float


@dataclass
class CalibrationEpoch:
    hive_id: int
    from_ts: int
    scale: float
    offset_kg: float


@dataclass
class SiteConfig:
    site_name: str
    timezone_offset_minutes: int
    day_start_minutes: int
    precision: int = 3
    tare_epoch: list[TareEpoch] = field(default_factory=list)
    calibration_epoch: list[CalibrationEpoch] = field(default_factory=list)
    alias_epoch: list[AliasEpoch] = field(default_factory=list)


def round_field(value: float, precision: int) -> float:
    return round(value, precision)


def logical_date(ts: int, cfg: SiteConfig) -> str:
    base = datetime.fromtimestamp(ts, tz=timezone.utc)
    shifted = base + timedelta(minutes=cfg.timezone_offset_minutes) - timedelta(
        minutes=cfg.day_start_minutes
    )
    return shifted.strftime("%Y-%m-%d")


def resolve_alias(raw_hive: int, ts: int, cfg: SiteConfig) -> int:
    best: AliasEpoch | None = None
    for alias in cfg.alias_epoch:
        if alias.raw_hive_id != raw_hive or alias.from_ts > ts:
            continue
        if alias.until_ts is not None and ts >= alias.until_ts:
            continue
        if best is None or alias.from_ts > best.from_ts:
            best = alias
    return best.canonical_hive_id if best else raw_hive


def resolve_calibration(canonical: int, ts: int, cfg: SiteConfig) -> tuple[float, float]:
    scale, offset, best = 1.0, 0.0, None
    for epoch in cfg.calibration_epoch:
        if epoch.hive_id != canonical or epoch.from_ts > ts:
            continue
        if best is None or epoch.from_ts > best:
            best = epoch.from_ts
            scale, offset = epoch.scale, epoch.offset_kg
    return scale, offset


def resolve_tare(canonical: int, ts: int, cfg: SiteConfig) -> float:
    tare, best = 0.0, None
    for epoch in cfg.tare_epoch:
        if epoch.hive_id != canonical or epoch.from_ts > ts:
            continue
        if best is None or epoch.from_ts > best:
            best = epoch.from_ts
            tare = epoch.tare_kg
    return tare


def net_kg(raw_hive: int, ts: int, grams: int, cfg: SiteConfig) -> tuple[int, float]:
    canonical = resolve_alias(raw_hive, ts, cfg)
    scale, offset = resolve_calibration(canonical, ts, cfg)
    calibrated = (grams / 1000.0) * scale + offset
    tare = resolve_tare(canonical, ts, cfg)
    return canonical, calibrated - tare


def parse_config_text(text: str) -> SiteConfig:
    raw = tomllib.loads(text)
    cfg = SiteConfig(
        site_name=raw["site_name"],
        timezone_offset_minutes=int(raw["timezone_offset_minutes"]),
        day_start_minutes=int(raw["day_start_minutes"]),
        precision=int(raw.get("precision", 3)),
    )
    for row in raw.get("tare_epoch", []):
        cfg.tare_epoch.append(
            TareEpoch(int(row["hive_id"]), int(row["from_ts"]), float(row["tare_kg"]))
        )
    for row in raw.get("calibration_epoch", []):
        cfg.calibration_epoch.append(
            CalibrationEpoch(
                int(row["hive_id"]),
                int(row["from_ts"]),
                float(row["scale"]),
                float(row["offset_kg"]),
            )
        )
    for row in raw.get("alias_epoch", []):
        cfg.alias_epoch.append(
            AliasEpoch(
                int(row["raw_hive_id"]),
                int(row["canonical_hive_id"]),
                int(row["from_ts"]),
                int(row["until_ts"]) if "until_ts" in row else None,
            )
        )
    return cfg


def write_config(path: Path, cfg: SiteConfig) -> None:
    lines = [
        f'site_name = "{cfg.site_name}"',
        f"timezone_offset_minutes = {cfg.timezone_offset_minutes}",
        f"day_start_minutes = {cfg.day_start_minutes}",
        f"precision = {cfg.precision}",
        "",
    ]
    for epoch in cfg.tare_epoch:
        lines.extend(
            [
                "[[tare_epoch]]",
                f"hive_id = {epoch.hive_id}",
                f"from_ts = {epoch.from_ts}",
                f"tare_kg = {epoch.tare_kg:.3f}",
                "",
            ]
        )
    for epoch in cfg.calibration_epoch:
        lines.extend(
            [
                "[[calibration_epoch]]",
                f"hive_id = {epoch.hive_id}",
                f"from_ts = {epoch.from_ts}",
                f"scale = {epoch.scale}",
                f"offset_kg = {epoch.offset_kg}",
                "",
            ]
        )
    for epoch in cfg.alias_epoch:
        lines.extend(
            [
                "[[alias_epoch]]",
                f"raw_hive_id = {epoch.raw_hive_id}",
                f"canonical_hive_id = {epoch.canonical_hive_id}",
                f"from_ts = {epoch.from_ts}",
            ]
        )
        if epoch.until_ts is not None:
            lines.append(f"until_ts = {epoch.until_ts}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


@dataclass
class LiveEvent:
    event_id: int
    timestamp: int
    raw_hive_id: int
    canonical_hive_id: int
    grams: int
    net_kg: float
    order: int
    live: bool = True


@dataclass
class ReferenceState:
    site: str
    events: dict[int, LiveEvent] = field(default_factory=dict)
    accepted_ids: set[int] = field(default_factory=set)
    next_order: int = 1
    stream_count: int = 0
    frame_count: int = 0
    duplicate_events: int = 0
    quarantined_frames: int = 0
    tombstoned_events: int = 0
    accepted_frames: int = 0
    streams: dict[str, dict] = field(default_factory=dict)
    frame_seq: int = 0
    state_epoch: int = 0


@dataclass
class QuarantineRow:
    source: str
    stream_index: int
    frame_index: int
    reason: str
    event_id: int | None


def take8(data: bytes, from_start: bool) -> int:
    buf = bytearray(8)
    if not data:
        return 0
    if from_start:
        n = min(8, len(data))
        buf[:n] = data[:n]
    else:
        n = min(8, len(data))
        buf[:n] = data[-n:]
    return int.from_bytes(buf, "little")


def stream_identity(source: str, kind: str, data: bytes) -> dict:
    byte_sum = 0
    for b in data:
        byte_sum = (byte_sum + b) & 0xFFFFFFFFFFFFFFFF
    return {
        "source": source,
        "kind": kind,
        "byte_len": len(data),
        "first8": take8(data, True),
        "last8": take8(data, False),
        "byte_sum": byte_sum,
    }


def parse_stream(data: bytes, offset: int) -> tuple[dict | None, str | None, int | None, int]:
    remaining = len(data) - offset
    if remaining <= 0:
        return None, "eof", None, 0
    if remaining >= 4 and data[offset : offset + 4] == b"HWSC":
        if remaining < V1_SIZE:
            return None, "truncated_tail", None, remaining
        return None, "unsupported_version", None, V1_SIZE
    if remaining < 4:
        return None, "truncated_tail", None, remaining
    if data[offset : offset + 4] != b"HWS2":
        if remaining < V2_SIZE:
            return None, "truncated_tail", None, remaining
        return None, "bad_magic", None, V2_SIZE
    if remaining < V2_SIZE:
        return None, "truncated_tail", None, remaining
    frame = data[offset : offset + V2_SIZE]
    version = frame[4]
    event_id = struct.unpack("<Q", frame[8:16])[0]
    frame_type = frame[5]
    if version != 2:
        return None, "unsupported_version", event_id, V2_SIZE
    if frame_type not in (1, 2, 3):
        return None, "unsupported_frame_type", event_id, V2_SIZE
    stored = struct.unpack("<I", frame[36:40])[0]
    computed = frame_checksum(frame[:36])
    if stored != computed:
        return None, "checksum", event_id, V2_SIZE
    parsed = {
        "frame_type": frame_type,
        "event_id": event_id,
        "timestamp": struct.unpack("<Q", frame[16:24])[0],
        "raw_hive_id": struct.unpack("<H", frame[24:26])[0],
        "grams": struct.unpack("<i", frame[26:30])[0],
        "correction_target": struct.unpack("<I", frame[30:34])[0],
    }
    return parsed, None, event_id, V2_SIZE


def find_target(state: ReferenceState, correction_target: int, frame_seq: int) -> int | None:
    candidates: list[tuple[int, int]] = []
    for event_id in state.accepted_ids:
        if (event_id & 0xFFFFFFFF) != correction_target:
            continue
        ev = state.events[event_id]
        if ev.order >= frame_seq:
            continue
        candidates.append((ev.order, event_id))
    if not candidates:
        return None
    return max(candidates)[1]


def store_event(state: ReferenceState, cfg: SiteConfig, event_id: int, ts: int, raw_hive: int, grams: int) -> None:
    canonical, net = net_kg(raw_hive, ts, grams, cfg)
    state.events[event_id] = LiveEvent(
        event_id=event_id,
        timestamp=ts,
        raw_hive_id=raw_hive,
        canonical_hive_id=canonical,
        grams=grams,
        net_kg=net,
        order=state.next_order,
        live=True,
    )
    state.next_order += 1
    state.accepted_ids.add(event_id)


def apply_frame(state: ReferenceState, cfg: SiteConfig, parsed: dict, frame_seq: int) -> str | None:
    ft = parsed["frame_type"]
    if ft == 1:
        if parsed["event_id"] in state.accepted_ids:
            state.duplicate_events += 1
            return None
        store_event(
            state,
            cfg,
            parsed["event_id"],
            parsed["timestamp"],
            parsed["raw_hive_id"],
            parsed["grams"],
        )
        state.accepted_frames += 1
        return None
    if ft == 2:
        if parsed["event_id"] in state.accepted_ids:
            state.duplicate_events += 1
            return None
        target = find_target(state, parsed["correction_target"], frame_seq)
        if target is None:
            return "missing_correction_target"
        ev = state.events[target]
        if not ev.live:
            state.accepted_ids.add(parsed["event_id"])
            return "stale_correction_target"
        ev.timestamp = parsed["timestamp"]
        ev.raw_hive_id = parsed["raw_hive_id"]
        ev.grams = parsed["grams"]
        canonical, net = net_kg(parsed["raw_hive_id"], parsed["timestamp"], parsed["grams"], cfg)
        ev.canonical_hive_id = canonical
        ev.net_kg = net
        ev.live = True
        state.accepted_frames += 1
        state.accepted_ids.add(parsed["event_id"])
        return None
    target = find_target(state, parsed["correction_target"], frame_seq)
    if target is None:
        state.duplicate_events += 1
        return None
    ev = state.events[target]
    if ev.live:
        ev.live = False
        state.tombstoned_events += 1
        state.accepted_frames += 1
    else:
        state.duplicate_events += 1
    return None


def fnv1a_hex(text: str) -> str:
    value = 14695981039346656037
    for ch in text.encode("utf-8"):
        value ^= ch
        value = (value * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return f"{value:016x}"


def json_num(value: float) -> str:
    return json.dumps(value)


def compute_audit_fingerprint(
    site: str,
    daily: list[dict],
    quarantine: list[dict],
    events: dict[int, LiveEvent],
    cfg: SiteConfig,
) -> str:
    lines = [f"site={site}"]
    for row in daily:
        lines.append(
            "daily|{date}|{hive_id}|{weight_delta_kg}|{samples}|{first_event_id}|{last_event_id}".format(
                date=row["date"],
                hive_id=row["hive_id"],
                weight_delta_kg=json_num(row["weight_delta_kg"]),
                samples=row["samples"],
                first_event_id=row["first_event_id"],
                last_event_id=row["last_event_id"],
            )
        )
    for row in quarantine:
        event = "null" if row["event_id"] is None else str(row["event_id"])
        lines.append(
            f"quarantine|{row['source']}|{row['stream_index']}|{row['frame_index']}|{row['reason']}|{event}"
        )
    for event_id in sorted(events):
        ev = events[event_id]
        if not ev.live:
            continue
        lines.append(
            "event|{event_id}|{timestamp}|{raw_hive_id}|{canonical_hive_id}|{grams}|{net_kg}|{order}".format(
                event_id=ev.event_id,
                timestamp=ev.timestamp,
                raw_hive_id=ev.raw_hive_id,
                canonical_hive_id=ev.canonical_hive_id,
                grams=ev.grams,
                net_kg=json_num(round_field(ev.net_kg, cfg.precision)),
                order=ev.order,
            )
        )
    lines.append("")
    return fnv1a_hex("\n".join(lines))


def build_outputs(
    state: ReferenceState,
    cfg: SiteConfig,
    quarantine: list[dict],
) -> tuple[list[dict], dict, list[dict]]:
    buckets: dict[tuple[str, int], list[LiveEvent]] = {}
    for ev in state.events.values():
        if not ev.live:
            continue
        day = logical_date(ev.timestamp, cfg)
        buckets.setdefault((day, ev.canonical_hive_id), []).append(ev)

    daily: list[dict] = []
    for (day, hive_id), events in sorted(buckets.items()):
        events.sort(key=lambda e: e.order)
        samples = len(events)
        delta = 0.0 if samples < 2 else events[-1].net_kg - events[0].net_kg
        daily.append(
            {
                "date": day,
                "hive_id": hive_id,
                "weight_delta_kg": round_field(delta, cfg.precision),
                "samples": samples,
                "first_event_id": events[0].event_id,
                "last_event_id": events[-1].event_id,
            }
        )

    hives = sorted({row["hive_id"] for row in daily if row["samples"] > 0})
    dates = sorted({row["date"] for row in daily})
    audit = compute_audit_fingerprint(state.site, daily, quarantine, state.events, cfg)
    summary = {
        "site": state.site,
        "total_delta_kg": round_field(sum(r["weight_delta_kg"] for r in daily), cfg.precision),
        "days_processed": len(dates),
        "hives_seen": hives,
        "accepted_frames": state.accepted_frames,
        "duplicate_events": state.duplicate_events,
        "quarantined_frames": state.quarantined_frames,
        "tombstoned_events": state.tombstoned_events,
        "state_frontier": {"stream_count": state.stream_count, "frame_count": state.frame_count},
        "audit_fingerprint": audit,
        "ready": bool(daily),
    }
    return daily, summary, quarantine


def reference_replay(
    manifest: dict,
    cfg: SiteConfig,
    stream_paths: dict[str, Path],
    base: ReferenceState | None = None,
    prefix_quarantine: list[dict] | None = None,
) -> tuple[list[dict], dict, list[dict], ReferenceState]:
    state = ReferenceState(site=manifest["site"])
    if base is not None:
        state = ReferenceState(
            site=base.site,
            events={k: LiveEvent(**vars(v)) for k, v in base.events.items()},
            accepted_ids=set(base.accepted_ids),
            next_order=base.next_order,
            stream_count=base.stream_count,
            frame_count=base.frame_count,
            duplicate_events=base.duplicate_events,
            quarantined_frames=base.quarantined_frames,
            tombstoned_events=base.tombstoned_events,
            accepted_frames=base.accepted_frames,
            streams={k: dict(v) for k, v in base.streams.items()},
            frame_seq=base.frame_seq,
            state_epoch=base.state_epoch,
        )
    quarantine: list[dict] = list(prefix_quarantine or [])

    for stream_index, stream in enumerate(manifest["streams"]):
        data = stream_paths[stream["path"]].read_bytes()
        identity = stream_identity(stream["source"], stream["kind"], data)
        start_slot = 0
        progress = state.streams.get(stream["source"])
        if progress and progress["identity"] == identity:
            start_slot = progress["consumed_slots"]

        offset = 0
        frame_index = 0
        while frame_index < start_slot and offset < len(data):
            parsed, reason, event_id, consumed = parse_stream(data, offset)
            if reason == "eof":
                break
            offset += consumed
            frame_index += 1

        while offset < len(data):
            state.frame_seq += 1
            current_seq = state.frame_seq
            parsed, reason, event_id, consumed = parse_stream(data, offset)
            if reason == "eof":
                break
            if reason is not None:
                state.quarantined_frames += 1
                quarantine.append(
                    {
                        "source": stream["source"],
                        "stream_index": stream_index,
                        "frame_index": frame_index,
                        "reason": reason,
                        "event_id": event_id,
                    }
                )
            else:
                missing = apply_frame(state, cfg, parsed, current_seq)
                if missing:
                    state.quarantined_frames += 1
                    quarantine.append(
                        {
                            "source": stream["source"],
                            "stream_index": stream_index,
                            "frame_index": frame_index,
                            "reason": missing,
                            "event_id": parsed["event_id"],
                        }
                    )
            offset += consumed
            frame_index += 1
            state.stream_count = stream_index + 1
            state.frame_count = frame_index

        state.streams[stream["source"]] = {
            "identity": identity,
            "consumed_slots": frame_index,
        }

    daily, summary, quarantine = build_outputs(state, cfg, quarantine)
    return daily, summary, quarantine, state


@pytest.fixture(scope="session", autouse=True)
def build_binary() -> None:
    proc = subprocess.run(
        ["cargo", "build", "--release", "--locked"],
        cwd=APP,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    BIN.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["install", "-m", "0755", "target/release/hive_scale", str(BIN)],
        cwd=APP,
        check=True,
    )


def run_scale(
    tmp_path: Path,
    manifest: dict,
    cfg: SiteConfig,
    stream_paths: dict[str, Path],
    *,
    resume: bool = False,
    compact: bool = False,
    prewrite_wrong: bool = False,
    prefix_quarantine: list[dict] | None = None,
    base_state: ReferenceState | None = None,
) -> tuple[list[dict], dict, list[dict]]:
    cfg_path = tmp_path / "apiary.toml"
    write_config(cfg_path, cfg)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    state_dir = tmp_path / "state"
    state_dir.mkdir(exist_ok=True)
    daily = tmp_path / "daily.jsonl"
    summary = tmp_path / "summary.json"
    quarantine = tmp_path / "quarantine.jsonl"

    if prewrite_wrong:
        daily.write_text(
            '{"date":"2099-01-01","hive_id":99,"weight_delta_kg":99.0,"samples":9,"first_event_id":1,"last_event_id":2}\n'
        )
        summary.write_text(json.dumps({"site": "wrong", "ready": True}))
        quarantine.write_text(
            '{"source":"x","stream_index":0,"frame_index":0,"reason":"checksum","event_id":1}\n'
        )

    cmd = [
        str(BIN),
        "--manifest",
        str(manifest_path),
        "--config",
        str(cfg_path),
        "--state-dir",
        str(state_dir),
        "--emit-daily",
        str(daily),
        "--emit-summary",
        str(summary),
        "--emit-quarantine",
        str(quarantine),
    ]
    if resume:
        cmd.append("--resume")
    if compact:
        cmd.append("--compact")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout

    got_daily = [json.loads(line) for line in daily.read_text(encoding="utf-8").splitlines() if line.strip()]
    got_summary = json.loads(summary.read_text(encoding="utf-8"))
    got_quarantine = [
        json.loads(line) for line in quarantine.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    exp_daily, exp_summary, exp_quarantine, _ = reference_replay(
        manifest, cfg, stream_paths, base=base_state, prefix_quarantine=prefix_quarantine
    )
    assert got_daily == exp_daily, got_daily
    assert got_summary == exp_summary, got_summary
    assert got_quarantine == exp_quarantine, got_quarantine
    return got_daily, got_summary, got_quarantine


def invoke_scale(
    tmp_path: Path,
    manifest: dict,
    cfg_path: Path,
    state_dir: Path,
    *,
    resume: bool = False,
    compact: bool = False,
    tag: str = "run",
) -> tuple[list[dict], dict, list[dict]]:
    state_dir.mkdir(parents=True, exist_ok=True)
    mpath = tmp_path / f"m_{tag}.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    daily = tmp_path / f"d_{tag}.jsonl"
    summary = tmp_path / f"s_{tag}.json"
    quar = tmp_path / f"q_{tag}.jsonl"
    cmd = [
        str(BIN),
        "--manifest",
        str(mpath),
        "--config",
        str(cfg_path),
        "--state-dir",
        str(state_dir),
        "--emit-daily",
        str(daily),
        "--emit-summary",
        str(summary),
        "--emit-quarantine",
        str(quar),
    ]
    if resume:
        cmd.append("--resume")
    if compact:
        cmd.append("--compact")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return (
        [json.loads(x) for x in daily.read_text().splitlines() if x.strip()],
        json.loads(summary.read_text()),
        [json.loads(x) for x in quar.read_text().splitlines() if x.strip()],
    )


def base_cfg(site: str = "north_yard") -> SiteConfig:
    return SiteConfig(
        site_name=site,
        timezone_offset_minutes=-480,
        day_start_minutes=360,
        precision=3,
        tare_epoch=[
            TareEpoch(1, 0, 42.5),
            TareEpoch(1, 1_700_100_000, 42.725),
            TareEpoch(2, 0, 10.0),
        ],
        calibration_epoch=[CalibrationEpoch(1, 0, 1.0, 0.0), CalibrationEpoch(2, 0, 1.0, 0.0)],
        alias_epoch=[AliasEpoch(201, 1, 0, 1_700_200_000)],
    )


def test_hive_scale_is_compiled_elf_binary() -> None:
    data = BIN.read_bytes()
    assert data[:4] == b"\x7fELF"


def test_fresh_replay_matches_reference_with_epochs_and_aliases(tmp_path: Path) -> None:
    cfg = base_cfg()
    s1 = tmp_path / "a.hws2"
    s2 = tmp_path / "b.hws2"
    ts_a = 1_700_000_000
    ts_b = 1_700_100_100
    s1.write_bytes(
        pack_v2(1, 5001, ts_a, 201, 85_000)
        + pack_v2(1, 5002, ts_a + 3600, 201, 86_000)
        + pack_v2(1, 5003, ts_b, 1, 86_500)
    )
    s2.write_bytes(pack_v2(1, 5004, ts_b + 7200, 2, 60_000))
    manifest = {
        "site": "north_yard",
        "streams": [
            {"source": "radio-a", "path": str(s1), "kind": "primary"},
            {"source": "radio-b", "path": str(s2), "kind": "primary"},
        ],
    }
    run_scale(tmp_path, manifest, cfg, {str(s1): s1, str(s2): s2})


def test_resume_two_pass_matches_single_fresh_replay(tmp_path: Path) -> None:
    cfg = base_cfg()
    s1 = tmp_path / "p1.hws2"
    s2 = tmp_path / "p2.hws2"
    s1.write_bytes(pack_v2(1, 6001, 1_700_010_000, 1, 43_000))
    s2.write_bytes(pack_v2(1, 6002, 1_700_020_000, 2, 55_000))
    part1 = {"site": "north_yard", "streams": [{"source": "a", "path": str(s1), "kind": "primary"}]}
    part2 = {"site": "north_yard", "streams": [{"source": "b", "path": str(s2), "kind": "primary"}]}
    full = {"site": "north_yard", "streams": part1["streams"] + part2["streams"]}
    paths = {str(s1): s1, str(s2): s2}
    cfg_path = tmp_path / "cfg.toml"
    write_config(cfg_path, cfg)
    state_a = tmp_path / "state_a"
    state_b = tmp_path / "state_b"
    invoke_scale(tmp_path, part1, cfg_path, state_a, tag="a1")
    two_pass_daily, two_pass_summary, two_pass_quar = invoke_scale(
        tmp_path, part2, cfg_path, state_a, resume=True, tag="a2"
    )
    fresh_daily, fresh_summary, fresh_quar = invoke_scale(tmp_path, full, cfg_path, state_b, tag="fresh")
    exp_daily, exp_summary, exp_quar, _ = reference_replay(full, cfg, paths)
    assert two_pass_daily == exp_daily
    assert two_pass_quar == exp_quar
    assert fresh_daily == exp_daily
    assert fresh_quar == exp_quar
    for key in exp_summary:
        if key == "state_frontier":
            continue
        assert two_pass_summary[key] == exp_summary[key]
        assert fresh_summary[key] == exp_summary[key]


def test_compacted_state_resume_matches_uncompacted_resume(tmp_path: Path) -> None:
    cfg = base_cfg()
    base = tmp_path / "base.hws2"
    backfill = tmp_path / "back.hws2"
    base.write_bytes(
        pack_v2(1, 7001, 1_700_030_000, 1, 44_000)
        + pack_v2(1, 7002, 1_700_040_000, 2, 56_000)
    )
    backfill.write_bytes(
        pack_v2(1, 7001, 1_700_030_000, 1, 44_000)
        + pack_v2(1, 7003, 1_700_050_000, 1, 45_000)
    )
    full = {"site": "north_yard", "streams": [{"source": "base", "path": str(base), "kind": "primary"}]}
    back = {"site": "north_yard", "streams": [{"source": "backfill", "path": str(backfill), "kind": "backfill"}]}
    cfg_path = tmp_path / "cfg.toml"
    write_config(cfg_path, cfg)
    compact_state = tmp_path / "compact_state"
    plain_state = tmp_path / "plain_state"
    invoke_scale(tmp_path, full, cfg_path, compact_state, compact=True, tag="c1")
    compact_daily, compact_summary, _ = invoke_scale(
        tmp_path, back, cfg_path, compact_state, resume=True, tag="c2"
    )
    invoke_scale(tmp_path, full, cfg_path, plain_state, tag="p1")
    plain_daily, plain_summary, _ = invoke_scale(tmp_path, back, cfg_path, plain_state, resume=True, tag="p2")
    base_state = reference_replay(full, cfg, {str(base): base})[3]
    exp_daily, exp_summary, _, _ = reference_replay(back, cfg, {str(backfill): backfill}, base_state)
    assert compact_daily == exp_daily
    assert plain_daily == exp_daily
    for key in exp_summary:
        if key == "state_frontier":
            continue
        assert compact_summary[key] == exp_summary[key]
        assert plain_summary[key] == exp_summary[key]


def test_duplicate_event_ids_are_idempotent_across_sources(tmp_path: Path) -> None:
    cfg = base_cfg()
    s1 = tmp_path / "s1.hws2"
    s2 = tmp_path / "s2.hws2"
    frame = pack_v2(1, 8001, 1_700_060_000, 1, 42_000)
    s1.write_bytes(frame)
    s2.write_bytes(frame)
    manifest = {
        "site": "north_yard",
        "streams": [
            {"source": "primary", "path": str(s1), "kind": "primary"},
            {"source": "backfill", "path": str(s2), "kind": "backfill"},
        ],
    }
    _, summary, _ = run_scale(tmp_path, manifest, cfg, {str(s1): s1, str(s2): s2})
    assert summary["duplicate_events"] == 1
    assert summary["accepted_frames"] == 1


def test_late_correction_moves_bucket_and_recomputes_delta(tmp_path: Path) -> None:
    cfg = base_cfg()
    stream = tmp_path / "corr.hws2"
    eid = 9001
    first_ts = 1_700_000_000
    new_ts = 1_700_200_100
    stream.write_bytes(
        pack_v2(1, eid, first_ts, 201, 85_000)
        + pack_v2(2, 9002, new_ts, 1, 86_000, correction_target=eid & 0xFFFFFFFF)
    )
    manifest = {
        "site": "north_yard",
        "streams": [{"source": "corr", "path": str(stream), "kind": "primary"}],
    }
    daily, _, _ = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    dates_for_hive1 = [row["date"] for row in daily if row["hive_id"] == 1]
    assert len(set(dates_for_hive1)) == 1
    assert dates_for_hive1[0] == logical_date(new_ts, cfg)


def test_tombstone_removes_event_without_poisoning_other_hives(tmp_path: Path) -> None:
    cfg = base_cfg()
    stream = tmp_path / "tomb.hws2"
    target = 10001
    stream.write_bytes(
        pack_v2(1, target, 1_700_070_000, 1, 43_500)
        + pack_v2(1, 10002, 1_700_070_500, 2, 57_000)
        + pack_v2(3, 10003, 1_700_071_000, 1, 0, correction_target=target & 0xFFFFFFFF)
        + pack_v2(3, 10004, 1_700_071_100, 1, 0, correction_target=99999)
    )
    manifest = {
        "site": "north_yard",
        "streams": [{"source": "tomb", "path": str(stream), "kind": "primary"}],
    }
    daily, summary, _ = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    hive1_rows = [r for r in daily if r["hive_id"] == 1]
    hive2_rows = [r for r in daily if r["hive_id"] == 2]
    assert hive1_rows == []
    assert hive2_rows and hive2_rows[0]["samples"] == 1
    assert summary["tombstoned_events"] == 1
    assert summary["duplicate_events"] == 1


def test_corrupt_checksum_bad_magic_and_truncated_tail_are_quarantined(tmp_path: Path) -> None:
    cfg = base_cfg()
    stream = tmp_path / "bad.hws2"
    good1 = pack_v2(1, 11001, 1_700_080_000, 1, 44_000)
    bad_chk = pack_v2(1, 11002, 1_700_080_100, 1, 44_100, bad_checksum=True)
    bad_mag = pack_v2(1, 11003, 1_700_080_200, 1, 44_200, bad_magic=True)
    good2 = pack_v2(1, 11004, 1_700_080_300, 1, 44_300)
    stream.write_bytes(good1 + bad_chk + bad_mag + good2 + good2[:10])
    manifest = {
        "site": "north_yard",
        "streams": [{"source": "bad", "path": str(stream), "kind": "primary"}],
    }
    daily, summary, quarantine = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    assert summary["accepted_frames"] == 2
    reasons = [row["reason"] for row in quarantine]
    assert "checksum" in reasons
    assert "bad_magic" in reasons
    assert "truncated_tail" in reasons
    bad_magic_rows = [row for row in quarantine if row["reason"] == "bad_magic"]
    assert bad_magic_rows and bad_magic_rows[0]["event_id"] is None
    assert len(daily) >= 1


def test_half_hour_timezone_and_day_start_boundary(tmp_path: Path) -> None:
    cfg = SiteConfig(
        site_name="edge-yard",
        timezone_offset_minutes=330,
        day_start_minutes=90,
        precision=3,
        tare_epoch=[TareEpoch(1, 0, 0.0)],
        calibration_epoch=[CalibrationEpoch(1, 0, 1.0, 0.0)],
    )
    stream = tmp_path / "tz.hws2"
    ts_before = 1_700_000_000
    ts_after = ts_before + 7200
    stream.write_bytes(
        pack_v2(1, 12001, ts_before, 1, 40_000)
        + pack_v2(1, 12002, ts_after, 1, 41_000)
    )
    manifest = {
        "site": "edge-yard",
        "streams": [{"source": "tz", "path": str(stream), "kind": "primary"}],
    }
    daily, _, _ = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    dates = sorted({row["date"] for row in daily})
    exp_dates = sorted({logical_date(ts_before, cfg), logical_date(ts_after, cfg)})
    assert dates == exp_dates


def test_output_overwrite_and_precomputed_cheat_fails(tmp_path: Path) -> None:
    cfg = base_cfg()
    stream = tmp_path / "fresh.hws2"
    stream.write_bytes(pack_v2(1, 13001, 1_700_090_000, 1, 45_000))
    manifest = {
        "site": "north_yard",
        "streams": [{"source": "fresh", "path": str(stream), "kind": "primary"}],
    }
    run_scale(tmp_path, manifest, cfg, {str(stream): stream}, prewrite_wrong=True)


def test_legacy_v1_frame_compatibility_or_explicit_quarantine(tmp_path: Path) -> None:
    cfg = base_cfg()
    v1 = tmp_path / "legacy.hsf"
    v2 = tmp_path / "after.hws2"
    v1.write_bytes(pack_v1(1_700_000_000, 1, 42000))
    v2.write_bytes(pack_v2(1, 14001, 1_700_095_000, 1, 46_000))
    manifest = {
        "site": "north_yard",
        "streams": [
            {"source": "legacy", "path": str(v1), "kind": "primary"},
            {"source": "modern", "path": str(v2), "kind": "primary"},
        ],
    }
    _, summary, quarantine = run_scale(tmp_path, manifest, cfg, {str(v1): v1, str(v2): v2})
    assert any(row["reason"] == "unsupported_version" for row in quarantine)
    assert summary["accepted_frames"] == 1


def test_resume_skips_consumed_matching_stream_but_replays_changed_backfill(tmp_path: Path) -> None:
    cfg = base_cfg()
    cfg_path = tmp_path / "cfg.toml"
    write_config(cfg_path, cfg)
    original = tmp_path / "orig.hws2"
    original.write_bytes(
        pack_v2(1, 15001, 1_700_100_000, 1, 43_000)
        + pack_v2(1, 15002, 1_700_100_100, 1, 44_000)
        + pack_v2(1, 15003, 1_700_100_200, 2, 55_000)
    )
    changed = tmp_path / "changed.hws2"
    changed.write_bytes(
        pack_v2(1, 15001, 1_700_100_000, 1, 43_000)
        + pack_v2(1, 15004, 1_700_100_300, 1, 45_000)
    )
    first = {
        "site": "north_yard",
        "streams": [{"source": "yard-a", "path": str(original), "kind": "primary"}],
    }
    resume_manifest = {
        "site": "north_yard",
        "streams": [
            {"source": "yard-a", "path": str(original), "kind": "primary"},
            {"source": "yard-a", "path": str(changed), "kind": "backfill"},
        ],
    }
    full_manifest = {
        "site": "north_yard",
        "streams": [
            {"source": "yard-a", "path": str(original), "kind": "primary"},
            {"source": "yard-a-backfill", "path": str(changed), "kind": "backfill"},
        ],
    }
    state = tmp_path / "state"
    invoke_scale(tmp_path, first, cfg_path, state, compact=True, tag="first")
    got_daily, got_summary, got_quar = invoke_scale(
        tmp_path, resume_manifest, cfg_path, state, resume=True, tag="resume"
    )
    exp_daily, exp_summary, exp_quar, _ = reference_replay(
        full_manifest,
        cfg,
        {str(original): original, str(changed): changed},
    )
    assert got_daily == exp_daily
    assert got_summary["audit_fingerprint"] == exp_summary["audit_fingerprint"]
    assert got_summary["duplicate_events"] == exp_summary["duplicate_events"]
    assert got_quar == exp_quar


def test_state_recovery_prefers_newest_valid_snapshot_and_reports_tmp_files(tmp_path: Path) -> None:
    cfg = base_cfg()
    cfg_path = tmp_path / "cfg.toml"
    write_config(cfg_path, cfg)
    seed = tmp_path / "seed.hws2"
    seed.write_bytes(pack_v2(1, 16001, 1_700_110_000, 1, 43_000))
    follow = tmp_path / "follow.hws2"
    follow.write_bytes(pack_v2(1, 16002, 1_700_110_100, 2, 56_000))
    first = {"site": "north_yard", "streams": [{"source": "seed", "path": str(seed), "kind": "primary"}]}
    second = {"site": "north_yard", "streams": [{"source": "follow", "path": str(follow), "kind": "primary"}]}
    state = tmp_path / "state"
    invoke_scale(tmp_path, first, cfg_path, state, compact=True, tag="seed")
    (state / "rollup_state.json").write_text("{ this is not valid json", encoding="utf-8")
    (state / "rollup_state.json.tmp").write_text("partial write", encoding="utf-8")
    prefix = [
        {
            "source": "",
            "stream_index": 0,
            "frame_index": 0,
            "reason": "state_recovery",
            "event_id": None,
        },
        {
            "source": "",
            "stream_index": 0,
            "frame_index": 0,
            "reason": "state_recovery",
            "event_id": None,
        },
    ]
    run_scale(
        tmp_path,
        second,
        cfg,
        {str(follow): follow},
        resume=True,
        prefix_quarantine=prefix,
        base_state=reference_replay(first, cfg, {str(seed): seed})[3],
    )


def test_low32_collision_target_resolution_and_correction_chain(tmp_path: Path) -> None:
    cfg = base_cfg()
    stream = tmp_path / "low32.hws2"
    low = 0x0000_00AB
    e1 = (0x1000_0000 << 32) | low
    e2 = (0x2000_0000 << 32) | low
    stream.write_bytes(
        pack_v2(1, e1, 1_700_120_000, 1, 43_000)
        + pack_v2(1, e2, 1_700_120_100, 1, 44_000)
        + pack_v2(2, 17001, 1_700_120_200, 1, 45_000, correction_target=low)
        + pack_v2(2, 17002, 1_700_120_300, 1, 46_000, correction_target=low)
    )
    manifest = {
        "site": "north_yard",
        "streams": [{"source": "low32", "path": str(stream), "kind": "primary"}],
    }
    daily, summary, _ = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    _, exp_summary, _, exp_state = reference_replay(manifest, cfg, {str(stream): stream})
    assert exp_state.events[e1].grams == 43_000
    assert exp_state.events[e2].grams == 46_000
    assert summary["audit_fingerprint"] == exp_summary["audit_fingerprint"]
    assert daily


def test_tombstone_after_correction_removes_current_bucket_only(tmp_path: Path) -> None:
    cfg = base_cfg()
    stream = tmp_path / "chain.hws2"
    target = 18001
    ts_a = 1_700_000_000
    ts_b = 1_700_200_100
    stream.write_bytes(
        pack_v2(1, target, ts_a, 201, 85_000)
        + pack_v2(1, 18002, ts_a + 100, 2, 56_000)
        + pack_v2(2, 18004, ts_b, 1, 86_500, correction_target=target & 0xFFFFFFFF)
        + pack_v2(1, 18003, ts_b, 1, 86_000)
        + pack_v2(3, 18005, ts_b + 10, 1, 0, correction_target=target & 0xFFFFFFFF)
    )
    manifest = {
        "site": "north_yard",
        "streams": [{"source": "chain", "path": str(stream), "kind": "primary"}],
    }
    daily, summary, _ = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    assert summary["tombstoned_events"] == 1
    hive1 = [r for r in daily if r["hive_id"] == 1]
    hive2 = [r for r in daily if r["hive_id"] == 2]
    assert hive1 and hive1[0]["samples"] == 1 and hive1[0]["first_event_id"] == 18003
    assert hive2 and hive2[0]["samples"] == 1


def test_stale_correction_target_is_quarantined_without_reviving_dead_event(tmp_path: Path) -> None:
    cfg = base_cfg()
    stream = tmp_path / "stale.hws2"
    target = 19001
    stream.write_bytes(
        pack_v2(1, target, 1_700_130_000, 1, 43_000)
        + pack_v2(3, 19002, 1_700_130_100, 1, 0, correction_target=target & 0xFFFFFFFF)
        + pack_v2(2, 19003, 1_700_130_200, 1, 44_000, correction_target=target & 0xFFFFFFFF)
    )
    manifest = {
        "site": "north_yard",
        "streams": [{"source": "stale", "path": str(stream), "kind": "primary"}],
    }
    daily, summary, quarantine = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    assert any(row["reason"] == "stale_correction_target" for row in quarantine)
    assert [r for r in daily if r["hive_id"] == 1] == []
    assert summary["tombstoned_events"] == 1


def test_unsupported_frame_type_has_event_id_and_preserves_frame_frontier(tmp_path: Path) -> None:
    cfg = base_cfg()
    stream = tmp_path / "unsupported.hws2"
    unsupported = pack_v2(9, 20001, 1_700_140_000, 1, 43_000)
    good = pack_v2(1, 20002, 1_700_140_100, 1, 44_000)
    stream.write_bytes(unsupported + good + good[:10])
    manifest = {
        "site": "north_yard",
        "streams": [{"source": "unsupported", "path": str(stream), "kind": "primary"}],
    }
    _, summary, quarantine = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    row = next(row for row in quarantine if row["reason"] == "unsupported_frame_type")
    assert row["event_id"] == 20001
    assert summary["state_frontier"]["frame_count"] == 3
    assert summary["accepted_frames"] == 1


def test_bad_magic_never_leaks_event_id_even_when_bytes_look_decodable(tmp_path: Path) -> None:
    cfg = base_cfg()
    stream = tmp_path / "magic.hws2"
    frame = pack_v2(1, 21001, 1_700_150_000, 1, 43_000, bad_magic=True)
    stream.write_bytes(frame + pack_v2(1, 21002, 1_700_150_100, 1, 44_000))
    manifest = {
        "site": "north_yard",
        "streams": [{"source": "magic", "path": str(stream), "kind": "primary"}],
    }
    _, _, quarantine = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    bad = next(row for row in quarantine if row["reason"] == "bad_magic")
    assert bad["event_id"] is None


def test_audit_fingerprint_is_stable_across_fresh_resume_and_compact_paths(tmp_path: Path) -> None:
    cfg = base_cfg()
    cfg_path = tmp_path / "cfg.toml"
    write_config(cfg_path, cfg)
    s1 = tmp_path / "af1.hws2"
    s2 = tmp_path / "af2.hws2"
    s1.write_bytes(pack_v2(1, 22001, 1_700_160_000, 1, 43_000))
    s2.write_bytes(pack_v2(1, 22002, 1_700_160_100, 2, 56_000))
    part1 = {"site": "north_yard", "streams": [{"source": "a", "path": str(s1), "kind": "primary"}]}
    part2 = {"site": "north_yard", "streams": [{"source": "b", "path": str(s2), "kind": "primary"}]}
    full = {"site": "north_yard", "streams": part1["streams"] + part2["streams"]}
    fresh_daily, fresh_summary, fresh_quar = invoke_scale(
        tmp_path, full, cfg_path, tmp_path / "fresh_state", tag="fresh"
    )
    resume_state = tmp_path / "resume_state"
    invoke_scale(tmp_path, part1, cfg_path, resume_state, tag="r1")
    resume_daily, resume_summary, resume_quar = invoke_scale(
        tmp_path, part2, cfg_path, resume_state, resume=True, tag="r2"
    )
    compact_state = tmp_path / "compact_state"
    invoke_scale(tmp_path, part1, cfg_path, compact_state, compact=True, tag="c1")
    compact_daily, compact_summary, compact_quar = invoke_scale(
        tmp_path, part2, cfg_path, compact_state, resume=True, tag="c2"
    )
    for key in fresh_summary:
        if key == "state_frontier":
            continue
        assert resume_summary[key] == fresh_summary[key]
        assert compact_summary[key] == fresh_summary[key]
    assert fresh_daily == resume_daily == compact_daily
    assert fresh_quar == resume_quar == compact_quar

    cfg2 = base_cfg()
    noisy = tmp_path / "noisy.hws2"
    noisy.write_bytes(pack_v2(1, 22001, 1_700_160_000, 1, 43_000, bad_checksum=True))
    noisy_manifest = {
        "site": "north_yard",
        "streams": [{"source": "a", "path": str(noisy), "kind": "primary"}],
    }
    _, noisy_summary, _ = run_scale(tmp_path, noisy_manifest, cfg2, {str(noisy): noisy})
    assert noisy_summary["audit_fingerprint"] != fresh_summary["audit_fingerprint"]


def test_epoch_tie_break_and_alias_until_boundary_after_correction(tmp_path: Path) -> None:
    cfg = SiteConfig(
        site_name="alias-yard",
        timezone_offset_minutes=0,
        day_start_minutes=0,
        precision=3,
        tare_epoch=[TareEpoch(1, 0, 0.0), TareEpoch(2, 0, 0.0)],
        calibration_epoch=[CalibrationEpoch(1, 0, 1.0, 0.0), CalibrationEpoch(2, 0, 1.0, 0.0)],
        alias_epoch=[
            AliasEpoch(201, 1, 100, 1_700_200_000),
            AliasEpoch(201, 2, 100, None),
        ],
    )
    stream = tmp_path / "alias.hws2"
    ts = 1_700_200_000
    stream.write_bytes(
        pack_v2(1, 23001, ts, 201, 40_000)
        + pack_v2(2, 23002, ts, 2, 41_000, correction_target=23001 & 0xFFFFFFFF)
    )
    manifest = {
        "site": "alias-yard",
        "streams": [{"source": "alias", "path": str(stream), "kind": "primary"}],
    }
    daily, _, _ = run_scale(tmp_path, manifest, cfg, {str(stream): stream})
    assert daily == [{"date": logical_date(ts, cfg), "hive_id": 2, "weight_delta_kg": 0.0, "samples": 1, "first_event_id": 23001, "last_event_id": 23001}]
