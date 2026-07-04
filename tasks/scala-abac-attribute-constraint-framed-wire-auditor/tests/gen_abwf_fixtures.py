#!/usr/bin/env python3
"""Generate verifier-only .abwf fixtures under tests/fixtures/."""

from __future__ import annotations

from pathlib import Path

from abac_wire import build_abwf

FULL_ATTRS = {"role": "analyst", "clearance": "secret"}


def fixture_dir() -> Path:
    here = Path(__file__).resolve().parent / "fixtures"
    for candidate in (here, Path("/tmp/abac-abwf-fixtures")):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return candidate
        except OSError:
            continue
    raise RuntimeError("no writable fixture directory for .abwf fixtures")


def fixture_root() -> Path:
    return fixture_dir()


def main() -> None:
    root = fixture_dir()
    root.joinpath("good_correct_crc.abwf").write_bytes(
        build_abwf(
            "TEN",
            "hidden-good",
            [
                ("TEN", 1, "access", 1, FULL_ATTRS, 100),
                ("TEN", 2, "access", 0, FULL_ATTRS, 200),
            ],
            correct_crc=True,
        )
    )
    bad = build_abwf(
        "TEN",
        "hidden-bad-crc",
        [("TEN", 1, "access", 1, FULL_ATTRS, 50)],
        correct_crc=True,
    )
    bad_arr = bytearray(bad)
    bad_arr[-1] ^= 0xFF
    root.joinpath("bad_crc.abwf").write_bytes(bytes(bad_arr))
    root.joinpath("out_of_order_eval_seq.abwf").write_bytes(
        build_abwf(
            "TEN",
            "hidden-ooo",
            [
                ("TEN", 2, "access", 0, FULL_ATTRS, 200),
                ("TEN", 1, "access", 1, FULL_ATTRS, 100),
            ],
            correct_crc=True,
        )
    )
    root.joinpath("missing_clearance.abwf").write_bytes(
        build_abwf(
            "TEN",
            "hidden-missing-attr",
            [("TEN", 1, "access", 1, {"role": "analyst"}, 100)],
            correct_crc=True,
        )
    )
    root.joinpath("duplicate_eval_seq.abwf").write_bytes(
        build_abwf(
            "TEN",
            "hidden-dup-seq",
            [
                ("TEN", 1, "access", 1, FULL_ATTRS, 100),
                ("TEN", 1, "access", 0, FULL_ATTRS, 150),
            ],
            correct_crc=True,
        )
    )
    root.joinpath("deny_only_after_permit.abwf").write_bytes(
        build_abwf(
            "TEN",
            "hidden-deny-trap",
            [
                ("TEN", 1, "policy-x", 1, FULL_ATTRS, 10),
                ("TEN", 2, "policy-x", 0, FULL_ATTRS, 20),
            ],
            correct_crc=True,
        )
    )


if __name__ == "__main__":
    main()
