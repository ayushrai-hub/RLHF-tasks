"""Independent export recompute for mavlink mission upload auditor anti-cheat."""

from __future__ import annotations

import functools
import hashlib
import json
import math
import sqlite3
import struct
import subprocess
from pathlib import Path
from typing import Any

EPOCH_BASE = 1_704_067_200
PROFILE_PATH = Path("/app/config/vehicle-profile.json")
_SERDE_F64_FMT = Path("/opt/verifier-scripts/serde-f64-fmt")


def _round3(value: float) -> float:
    return round(value, 3)


def _vehicle_profile(vehicle_id: str) -> dict:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    vehicles = profile["vehicles"]
    if vehicle_id not in vehicles:
        raise KeyError(f"unknown vehicle_id {vehicle_id!r}")
    return vehicles[vehicle_id]


def _home_alt_m(vehicle_id: str) -> float:
    return float(_vehicle_profile(vehicle_id)["home_alt_m"])


def _alt_meters(alt_mm: int, frame: int, home_alt_m: float) -> float:
    raw = alt_mm / 1000.0
    if frame == 3:
        return _round3(raw - home_alt_m)
    return _round3(raw)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _upload_qc_pass(waypoints: list[dict], total_distance_m: float, vehicle_id: str) -> bool:
    vehicle = _vehicle_profile(vehicle_id)
    max_route_m = float(vehicle["max_route_m"])
    max_rel_alt_m = float(vehicle["max_rel_alt_m"])
    if total_distance_m > max_route_m:
        return False
    for wp in waypoints:
        if wp["frame"] == 3 and (
            wp["alt_meters"] > max_rel_alt_m or wp["alt_meters"] < -max_rel_alt_m
        ):
            return False
    return True


@functools.lru_cache(maxsize=4096)
def _serde_f64_from_bits(bits: bytes) -> str:
    """Match Rust serde_json::to_string for one f64 (image-built helper)."""
    value = struct.unpack("d", bits)[0]
    if not math.isfinite(value):
        raise ValueError(f"non-finite f64 not allowed in audit_hash payload: {value}")
    if not _SERDE_F64_FMT.is_file():
        raise FileNotFoundError(f"missing verifier helper: {_SERDE_F64_FMT}")
    proc = subprocess.run(
        [str(_SERDE_F64_FMT)],
        input=f"{value}\n",
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError("serde-f64-fmt returned empty output")
    return out


def _serde_f64(value: float) -> str:
    return _serde_f64_from_bits(struct.pack("d", value))


def _serde_json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _serde_waypoint_json(wp: dict[str, Any]) -> str:
    return (
        "{"
        f'"seq":{int(wp["seq"])},'
        f'"lat_deg":{_serde_f64(float(wp["lat_deg"]))},'
        f'"lon_deg":{_serde_f64(float(wp["lon_deg"]))},'
        f'"alt_meters":{_serde_f64(float(wp["alt_meters"]))},'
        f'"frame":{int(wp["frame"])}'
        "}"
    )


def _audit_hash(
    vehicle_id: str,
    upload_id: str,
    waypoints: list[dict],
    total_distance_m: float,
) -> str:
    wps = ",".join(_serde_waypoint_json(wp) for wp in waypoints)
    payload = (
        "{"
        f'"vehicle_id":{_serde_json_string(vehicle_id)},'
        f'"upload_id":{_serde_json_string(upload_id)},'
        f'"waypoints":[{wps}],'
        f'"total_distance_m":{_serde_f64(float(total_distance_m))}'
        "}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _exported_at_unix(
    conn: sqlite3.Connection,
    vehicle_id: str,
    upload_id: str,
    *,
    epoch_base: int,
    epoch_mode: str = "max_seq",
) -> int:
    """Compute export clock per /app/docs/db-schema.md.

    epoch_mode:
      - ``max_seq`` — ``MISSION_EPOCH_BASE + max(seq)`` within the export upload (correct).
      - ``id_desc`` — epoch from last inserted row (``ORDER BY rowid DESC``) — partial-fix trap.
      - ``vehicle_wide`` — max seq on the vehicle across all uploads.
      - ``global`` — max seq in the whole database.
    """
    if epoch_mode == "global":
        row = conn.execute("SELECT COALESCE(MAX(seq), 0) AS m FROM waypoints").fetchone()
        return epoch_base + int(row["m"])
    if epoch_mode == "vehicle_wide":
        row = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS m FROM waypoints WHERE vehicle_id = ?",
            (vehicle_id,),
        ).fetchone()
        return epoch_base + int(row["m"])
    if epoch_mode == "id_desc":
        row = conn.execute(
            """
            SELECT seq FROM waypoints
            WHERE vehicle_id = ? AND upload_id = ?
            ORDER BY rowid DESC LIMIT 1
            """,
            (vehicle_id, upload_id),
        ).fetchone()
        seq = int(row["seq"]) if row is not None else 0
        return epoch_base + seq
    row = conn.execute(
        """
        SELECT COALESCE(MAX(seq), 0) AS m FROM waypoints
        WHERE vehicle_id = ? AND upload_id = ?
        """,
        (vehicle_id, upload_id),
    ).fetchone()
    return epoch_base + int(row["m"])


def expected_export(
    db_path: Path,
    vehicle_id: str,
    upload_id: str,
    *,
    epoch_base: int = EPOCH_BASE,
    epoch_mode: str = "max_seq",
) -> dict:
    """Build the export JSON contract from persisted SQLite rows."""
    home = _home_alt_m(vehicle_id)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT seq, lat_e7, lon_e7, alt_mm, frame, flags
        FROM waypoints
        WHERE vehicle_id = ? AND upload_id = ?
        ORDER BY seq ASC
        """,
        (vehicle_id, upload_id),
    ).fetchall()

    waypoints = []
    for row in rows:
        if int(row["flags"]) & 0x04:
            continue
        waypoints.append(
            {
                "seq": int(row["seq"]),
                "lat_deg": row["lat_e7"] / 1e7,
                "lon_deg": row["lon_e7"] / 1e7,
                "alt_meters": _alt_meters(int(row["alt_mm"]), int(row["frame"]), home),
                "frame": int(row["frame"]),
            }
        )

    raw_rows = list(rows)
    total = 0.0
    for i in range(1, len(raw_rows)):
        if int(raw_rows[i]["flags"]) & 0x02:
            continue
        lat1 = raw_rows[i - 1]["lat_e7"] / 1e7
        lon1 = raw_rows[i - 1]["lon_e7"] / 1e7
        lat2 = raw_rows[i]["lat_e7"] / 1e7
        lon2 = raw_rows[i]["lon_e7"] / 1e7
        total += _haversine_m(lat1, lon1, lat2, lon2)

    total_distance_m = _round3(total)
    exported_at_unix = _exported_at_unix(
        conn, vehicle_id, upload_id, epoch_base=epoch_base, epoch_mode=epoch_mode
    )
    conn.close()
    return {
        "vehicle_id": vehicle_id,
        "upload_id": upload_id,
        "waypoints": waypoints,
        "total_distance_m": total_distance_m,
        "exported_at_unix": exported_at_unix,
        "upload_qc_pass": _upload_qc_pass(waypoints, total_distance_m, vehicle_id),
        "audit_hash": _audit_hash(vehicle_id, upload_id, waypoints, total_distance_m),
    }
