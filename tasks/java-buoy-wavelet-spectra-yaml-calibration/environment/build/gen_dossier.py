#!/usr/bin/env python3
"""Generate long-form coastal operations dossier (~70k+ tokens)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "coastal-operations-dossier.md"

CANONICAL = """
## FINAL CALIBRATION MEMO (authoritative)

Config merge: YAML storm profile first, TOML site overlay wins conflicts.
Drift: subtract rate_pa_per_hour times hours since reference_epoch_ms.
Gaps: linear interpolation only — never zero-fill missing pressure rows.
COI half-width per scale: coi_w = ceil(coi_factor * scale) integer samples; valid t when coi_w <= t < n - coi_w.
Scale frequency mapping: freq_hz = sample_rate_hz / scale (pipeline contract, not textbook Morlet f0).
Hs meters = 4 * sqrt(m0) on COI-valid elevation samples.
Peak period = 1/f_peak at max COI-valid Morlet power within band limits using freq_hz above.
samples_used = total input CSV row count including gap-filled quality_flag=0 rows.
Sample rate always from merged profile sample_rate_hz (ignore manifest hints).
"""


def main() -> None:
    chunks: list[str] = [
        "# Coastal Buoy Operations Dossier\n",
        "Compiled analyst notebook — deployment notes, calibration memos, email excerpts.\n",
        CANONICAL,
    ]
    for i in range(900):
        chunks.append(
            f"\n## Deployment segment {i:04d}\n"
            f"Buoy {i % 17:02d} serviced after storm window. Pressure sensor drift reviews "
            f"reference epoch alignment and YAML/TOML precedence per site calibration playbook. "
            f"Wavelet edge effects discussed in thread {1000 + i}; cone-of-influence masking "
            f"must exclude scales near series boundaries before Hs/Tp export.\n"
            f"From: ops-lead@coastal.example\n"
            f"Subject: Re: storm {i} spectra QA — use linear gap fill, not zero hold.\n"
            f"Analyst note: confirm drift subtraction sign before Morlet run.\n"
        )
    text = "".join(chunks)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} chars={len(text)}")


if __name__ == "__main__":
    main()
