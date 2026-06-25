#!/usr/bin/env python3
"""Generate the PSON January 2024 sensors.db fixture (authoring script only — not shipped in the image)."""

from __future__ import annotations

import gzip
import math
import sqlite3
import sys
from pathlib import Path

# Station-specific background parameters and synthetic anomaly windows.
# Kept in the authoring script so the Docker build never embeds event metadata.
STATION_PROFILES = [
    {
        "code": "AXID01",
        "seed": 10001,
        "base": 404.50,
        "drift": 0.10,
        "sigma": 0.003,
        "anomalies": [("2024-01-15T04:00:00.000Z", 21, -0.340)],
    },
    {
        "code": "AXID02",
        "seed": 20001,
        "base": 420.60,
        "drift": 0.08,
        "sigma": 0.003,
        "anomalies": [("2024-01-18T11:30:00.000Z", 12, 0.255)],
    },
    {
        "code": "NEMO01",
        "seed": 30001,
        "base": 340.60,
        "drift": 0.12,
        "sigma": 0.003,
        "anomalies": [("2024-01-22T08:00:00.000Z", 27, -0.41964)],
    },
    {
        "code": "JUAN01",
        "seed": 40001,
        "base": 228.90,
        "drift": 0.05,
        "sigma": 0.003,
        "anomalies": [("2024-01-10T15:00:00.000Z", 12, 0.218)],
    },
    {
        "code": "COAX01",
        "seed": 50001,
        "base": 486.10,
        "drift": 0.15,
        "sigma": 0.005,
        "anomalies": [("2024-01-25T20:00:00.000Z", 30, 0.412)],
    },
]


def lcg_floats(seed: int, n: int) -> list[float]:
    a, c, m = 1664525, 1013904223, 2**32
    state = seed & 0xFFFFFFFF
    out: list[float] = []
    for _ in range(n):
        state = (a * state + c) & 0xFFFFFFFF
        out.append(state / m - 0.5)
    return out


def gauss(seed: int, n: int) -> list[float]:
    raw = lcg_floats(seed, n + 4)
    out: list[float] = []
    i = 0
    while len(out) < n and i + 1 < len(raw):
        u1 = max(raw[i] + 0.5, 1e-12)
        u2 = (raw[i + 1] + 0.5) * 2.0 * math.pi
        r = math.sqrt(-2.0 * math.log(u1))
        out.append(r * math.cos(u2))
        if len(out) < n:
            out.append(r * math.sin(u2))
        i += 2
    return out[:n]


def timestamps() -> list[str]:
    ts: list[str] = []
    for day in range(1, 32):
        for hour in range(24):
            for minute in range(0, 60, 10):
                ts.append(f"2024-01-{day:02d}T{hour:02d}:{minute:02d}:00.000Z")
    return ts


def sample_index(ts: str) -> int:
    day, hour, minute = int(ts[8:10]), int(ts[11:13]), int(ts[14:16])
    return (day - 1) * 144 + hour * 6 + minute // 10


def synthesize_pressure(
    seed: int,
    n: int,
    base: float,
    drift: float,
    sigma: float,
    anomalies: list[tuple[str, int, float]],
) -> list[float]:
    noise = gauss(seed, n)
    windows = [(sample_index(start), sample_index(start) + length, amp) for start, length, amp in anomalies]
    out: list[float] = []
    for i in range(n):
        value = (
            base
            + drift * i / n
            + 0.0008 * math.sin(2 * math.pi * i / 144.0)
            + 0.0003 * math.sin(2 * math.pi * i / 72.25)
            + sigma * noise[i]
        )
        for start, end, amp in windows:
            if start <= i < end:
                value += amp
        out.append(round(value, 6))
    return out


def seed_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE stations (
            code TEXT PRIMARY KEY, full_name TEXT NOT NULL,
            latitude REAL NOT NULL, longitude REAL NOT NULL,
            depth_m REAL NOT NULL, deployment_date TEXT NOT NULL, status TEXT NOT NULL)"""
    )
    cur.execute(
        """CREATE TABLE readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL, sensor_type TEXT NOT NULL,
            timestamp TEXT NOT NULL, raw_value REAL NOT NULL, unit TEXT NOT NULL,
            FOREIGN KEY (station_id) REFERENCES stations(code))"""
    )
    cur.execute("CREATE INDEX idx ON readings(station_id, sensor_type, timestamp)")

    cur.executemany(
        "INSERT INTO stations VALUES (?,?,?,?,?,?,?)",
        [
            ("AXID01", "Axial Seamount Primary Pressure Array", 45.9547, -130.0085, 4145.0, "2021-07-15", "active"),
            ("AXID02", "Axial Seamount Secondary Monitoring Array", 45.9531, -130.0094, 4162.0, "2021-07-17", "active"),
            ("NEMO01", "Northern Extension Monitor Station", 47.1203, -128.8847, 3822.0, "2020-09-03", "active"),
            ("JUAN01", "Juan de Fuca Ridge Vent Field Station", 47.9667, -129.1083, 2318.0, "2019-04-22", "active"),
            ("COAX01", "Cascadia Basin Deep-Sea Outpost", 46.2185, -129.7294, 4831.0, "2022-03-11", "active"),
        ],
    )

    ts = timestamps()
    n = len(ts)
    rows: list[tuple[str, str, str, float, str]] = []

    for profile in STATION_PROFILES:
        sid = profile["code"]
        pressure = synthesize_pressure(
            profile["seed"],
            n,
            profile["base"],
            profile["drift"],
            profile["sigma"],
            profile["anomalies"],
        )
        for i, stamp in enumerate(ts):
            rows.append((sid, "pressure", stamp, pressure[i], "kPa"))

    cur.executemany(
        "INSERT INTO readings(station_id,sensor_type,timestamp,raw_value,unit) VALUES(?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    print(f"Seeded {db_path}: {len(rows)} readings")


def main() -> None:
    default = Path(__file__).resolve().parent.parent / "environment" / "data" / "sensors.db"
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    if target.exists():
        target.unlink()
    seed_database(target)
    gz_target = target.with_suffix(target.suffix + ".gz")
    with open(target, "rb") as src, gzip.open(gz_target, "wb", compresslevel=9) as dst:
        dst.writelines(src)
    target.unlink()
    print(f"Wrote compressed fixture {gz_target}")


if __name__ == "__main__":
    main()
