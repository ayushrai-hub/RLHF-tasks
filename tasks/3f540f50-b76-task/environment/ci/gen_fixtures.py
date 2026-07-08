#!/usr/bin/env python3
"""Generate deterministic Modbus register capture fixtures for verifier and practice trees."""

from __future__ import annotations

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"


def modbus_crc(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def frame(
    *,
    segment: int,
    profile: int,
    slave: int,
    func: int,
    reg: int,
    count: int,
    seq: int,
    payload: bytes,
) -> bytes:
    header = struct.pack(
        ">4sBBBBHHIH",
        b"MREG",
        segment,
        profile,
        slave,
        func,
        reg,
        count,
        seq,
        len(payload),
    )
    body = header + payload
    crc = modbus_crc(body)
    return body + struct.pack("<H", crc)


def read_payload(values: list[int], width: int = 2) -> bytes:
    out = bytearray()
    for v in values:
        if width == 2:
            out.extend(struct.pack(">H", v))
        else:
            out.extend(struct.pack("<I", v))
    return bytes(out)


def write_blob(path: Path, frames: list[bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(frames))


def practice_fixtures() -> None:
    d = FIX / "practice"
    write_blob(
        d / "alpha.mreg",
        [
            frame(
                segment=3,
                profile=1,
                slave=11,
                func=0x03,
                reg=100,
                count=2,
                seq=1,
                payload=read_payload([1200, 1201]),
            ),
            frame(
                segment=3,
                profile=1,
                slave=11,
                func=0x03,
                reg=200,
                count=1,
                seq=2,
                payload=read_payload([42]),
            ),
            frame(
                segment=4,
                profile=1,
                slave=12,
                func=0x03,
                reg=50,
                count=1,
                seq=3,
                payload=read_payload([7]),
            ),
        ],
    )
    write_blob(
        d / "beta.mreg",
        [
            frame(
                segment=3,
                profile=1,
                slave=11,
                func=0x03,
                reg=300,
                count=2,
                seq=4,
                payload=read_payload([9, 10]),
            ),
            frame(
                segment=3,
                profile=1,
                slave=13,
                func=0x83,
                reg=10,
                count=0,
                seq=5,
                payload=bytes([0x02]),
            ),
        ],
    )
    (d / ".mregorder").write_text(
        json.dumps({"priority": ["beta.mreg", "alpha.mreg"]}, indent=2) + "\n",
        encoding="utf-8",
    )


def regression_fixtures() -> None:
    base = FIX / "regression"

    write_blob(
        base / "crc_noise" / "solo.mreg",
        [
            frame(
                segment=1,
                profile=1,
                slave=1,
                func=0x03,
                reg=1,
                count=1,
                seq=1,
                payload=read_payload([100]),
            )
        ],
    )
    blob = (base / "crc_noise" / "solo.mreg").read_bytes()
    bad = bytearray(blob)
    bad[-2] ^= 0xFF
    (base / "crc_noise" / "solo.mreg").write_bytes(bytes(bad))

    write_blob(
        base / "duplicate_seq" / "dup.mreg",
        [
            frame(
                segment=2,
                profile=1,
                slave=2,
                func=0x03,
                reg=10,
                count=1,
                seq=7,
                payload=read_payload([1]),
            ),
            frame(
                segment=2,
                profile=1,
                slave=2,
                func=0x03,
                reg=11,
                count=1,
                seq=7,
                payload=read_payload([2]),
            ),
        ],
    )

    write_blob(
        base / "slave_reject" / "mix.mreg",
        [
            frame(
                segment=1,
                profile=1,
                slave=99,
                func=0x03,
                reg=1,
                count=1,
                seq=1,
                payload=read_payload([5]),
            ),
            frame(
                segment=1,
                profile=1,
                slave=11,
                func=0x03,
                reg=2,
                count=1,
                seq=2,
                payload=read_payload([6]),
            ),
        ],
    )

    write_blob(
        base / "checkpoint_skip" / "lane.mreg",
        [
            frame(
                segment=1,
                profile=1,
                slave=11,
                func=0x00,
                reg=0,
                count=0,
                seq=0,
                payload=b"",
            ),
            frame(
                segment=1,
                profile=1,
                slave=11,
                func=0x03,
                reg=5,
                count=1,
                seq=1,
                payload=read_payload([55]),
            ),
        ],
    )

    write_blob(
        base / "continue_seed" / "relay.mreg",
        [
            frame(
                segment=5,
                profile=1,
                slave=11,
                func=0x03,
                reg=1,
                count=1,
                seq=10,
                payload=read_payload([1000]),
            ),
        ],
    )
    (base / "continue_seed" / ".mreg_continue").write_text("", encoding="utf-8")

    write_blob(
        base / "order_overlay" / "first.mreg",
        [
            frame(
                segment=1,
                profile=1,
                slave=11,
                func=0x03,
                reg=1,
                count=1,
                seq=1,
                payload=read_payload([11]),
            ),
        ],
    )
    write_blob(
        base / "order_overlay" / "second.mreg",
        [
            frame(
                segment=1,
                profile=1,
                slave=11,
                func=0x03,
                reg=2,
                count=1,
                seq=2,
                payload=read_payload([22]),
            ),
        ],
    )
    (base / "order_overlay" / ".mregorder").write_text(
        json.dumps({"priority": ["second.mreg", "first.mreg"]}, indent=2) + "\n",
        encoding="utf-8",
    )

    (base / "empty_scan" / "notes.txt").write_text("no capture files here\n", encoding="utf-8")


def main() -> None:
    practice_fixtures()
    regression_fixtures()
    print("fixtures ok")


if __name__ == "__main__":
    main()
