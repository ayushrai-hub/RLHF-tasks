#!/usr/bin/env python3
"""Generate bundled buoy pressure series and manifest fixtures."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
SERIES = FIX / "series"
MANIFESTS = FIX / "manifests"
PROBES = Path(os.environ.get("BUOY_PROBE_BUILD_DIR", "/tmp/buoy-spectra-probes-build"))


def synth_series(
    run_id: str,
    *,
    sample_rate_hz: float,
    n: int,
    wave_amp_pa: float,
    wave_period_s: float,
    drift_rate: float,
    ref_epoch_ms: int,
    gap_indices: set[int] | None = None,
) -> list[tuple[int, float, int]]:
    gap_indices = gap_indices or set()
    rows: list[tuple[int, float, int]] = []
    dt_ms = int(1000 / sample_rate_hz)
    for i in range(n):
        t_ms = ref_epoch_ms + i * dt_ms
        hours = (t_ms - ref_epoch_ms) / 3_600_000.0
        drift = drift_rate * hours
        phase = 2 * math.pi * (i / sample_rate_hz) / wave_period_s
        wave = wave_amp_pa * math.sin(phase)
        base = 101325.0 + drift + wave
        flag = 0 if i in gap_indices else 1
        rows.append((t_ms, base, flag))
    return rows


def write_csv(path: Path, rows: list[tuple[int, float, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["timestamp_ms,pressure_pa,quality_flag"]
    for t, p, q in rows:
        lines.append(f"{t},{p:.6f},{q}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ref = 1_700_000_000_000
    write_csv(
        SERIES / "storm-alpha.csv",
        synth_series(
            "storm-alpha",
            sample_rate_hz=2.0,
            n=256,
            wave_amp_pa=850.0,
            wave_period_s=8.5,
            drift_rate=0.12,
            ref_epoch_ms=ref,
            gap_indices={40, 41, 120},
        ),
    )
    write_manifest(
        MANIFESTS / "storm-alpha.json",
        {
            "run_id": "storm-alpha",
            "series_path": "series/storm-alpha.csv",
            "profile": "profiles/storm-processing.yaml",
            "toml_overlay": "profiles/site-calibration.toml",
        },
    )

    write_csv(
        SERIES / "storm-beta.csv",
        synth_series(
            "storm-beta",
            sample_rate_hz=2.0,
            n=200,
            wave_amp_pa=620.0,
            wave_period_s=6.2,
            drift_rate=0.09,
            ref_epoch_ms=ref + 86_400_000,
            gap_indices={15, 16, 17, 90},
        ),
    )
    write_manifest(
        MANIFESTS / "storm-beta.json",
        {
            "run_id": "storm-beta",
            "series_path": "series/storm-beta.csv",
            "profile": "profiles/storm-processing.yaml",
            "toml_overlay": "profiles/site-calibration.toml",
            "sample_rate_hz": 1.0,
        },
    )

    if PROBES.exists():
        for p in PROBES.rglob("*"):
            if p.is_file():
                p.unlink()

    write_csv(
        PROBES / "series" / "probe-shift.csv",
        synth_series(
            "probe-shift",
            sample_rate_hz=2.0,
            n=180,
            wave_amp_pa=540.0,
            wave_period_s=7.1,
            drift_rate=0.22,
            ref_epoch_ms=ref + 172_800_000,
            gap_indices={55, 56},
        ),
    )
    write_manifest(
        PROBES / "manifests" / "probe-shift.json",
        {
            "run_id": "probe-shift",
            "series_path": "series/probe-shift.csv",
            "profile": "profiles/storm-processing.yaml",
            "toml_overlay": "profiles/site-calibration.toml",
        },
    )

    write_csv(
        PROBES / "series" / "probe-coarse.csv",
        synth_series(
            "probe-coarse",
            sample_rate_hz=2.0,
            n=160,
            wave_amp_pa=710.0,
            wave_period_s=9.4,
            drift_rate=0.15,
            ref_epoch_ms=ref + 259_200_000,
            gap_indices={22, 23, 24, 88},
        ),
    )
    write_manifest(
        PROBES / "manifests" / "probe-coarse.json",
        {
            "run_id": "probe-coarse",
            "series_path": "series/probe-coarse.csv",
            "profile": "profiles/storm-processing.yaml",
            "toml_overlay": "profiles/site-calibration.toml",
        },
    )


if __name__ == "__main__":
    main()
