#!/usr/bin/env python3
"""Generate bundled v2 hive-scale fixtures and manifests."""

from __future__ import annotations

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STREAMS = ROOT / "fixtures" / "streams"
MANIFESTS = ROOT / "fixtures" / "manifests"


def checksum(body: bytes) -> int:
    return sum(body) & 0xFFFFFFFF


def v2_frame(
    frame_type: int,
    event_id: int,
    ts: int,
    raw_hive: int,
    grams: int,
    correction_target: int = 0,
    source_seq: int = 0,
) -> bytes:
    body = bytearray(36)
    body[0:4] = b"HWS2"
    body[4] = 2
    body[5] = frame_type
    struct.pack_into("<H", body, 6, 0)
    struct.pack_into("<Q", body, 8, event_id)
    struct.pack_into("<Q", body, 16, ts)
    struct.pack_into("<H", body, 24, raw_hive)
    struct.pack_into("<i", body, 26, grams)
    struct.pack_into("<I", body, 30, correction_target)
    struct.pack_into("<H", body, 34, source_seq)
    return bytes(body) + struct.pack("<I", checksum(bytes(body)))


def v1_frame(ts: int, hive: int, grams: int) -> bytes:
    body = b"HWSC" + struct.pack("<Q", ts) + bytes([hive & 0xFF]) + struct.pack("<I", grams)
    chk = sum(body) & 0xFFFFFFFF
    return body + struct.pack("<I", chk) + b"\x00\x00\x00"


def main() -> None:
    STREAMS.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)

    demo_a = v2_frame(1, 1001, 1_700_000_000, 201, 85_000) + v2_frame(
        1, 1002, 1_700_003_600, 1, 86_000
    )
    (STREAMS / "demo_a.hws2").write_bytes(demo_a)

    demo_b = (
        v2_frame(1, 2001, 1_700_086_400, 2, 50_000)
        + v2_frame(1, 2002, 1_700_090_000, 2, 51_200)
        + v2_frame(1, 2003, 1_700_177_000, 2, 52_000)
    )
    (STREAMS / "demo_b.hws2").write_bytes(demo_b)

    (STREAMS / "demo_backfill.hws2").write_bytes(
        v2_frame(1, 1001, 1_700_000_000, 201, 85_000)
    )
    (STREAMS / "legacy_v1.hsf").write_bytes(v1_frame(1_700_000_000, 1, 42000))

    part1 = {
        "site": "north_yard",
        "streams": [
            {
                "source": "yard-a-radio-1",
                "path": "/app/fixtures/streams/demo_a.hws2",
                "kind": "primary",
            }
        ],
    }
    part2 = {
        "site": "north_yard",
        "streams": [
            {
                "source": "yard-b-radio-2",
                "path": "/app/fixtures/streams/demo_b.hws2",
                "kind": "primary",
            }
        ],
    }
    full = {
        "site": "north_yard",
        "streams": part1["streams"] + part2["streams"],
    }
    for name, payload in [
        ("demo_part1.json", part1),
        ("demo_part2.json", part2),
        ("demo_full.json", full),
    ]:
        (MANIFESTS / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
