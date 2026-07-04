"""Shared RTCM3 reference codec for verifier tests."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

CRC24Q_POLY = 0x1864CFB


def crc24q(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            if crc & 0x800000:
                crc = ((crc << 1) ^ CRC24Q_POLY) & 0xFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFF
    return crc


def encode_frame(
    station_id: int,
    mountpoint: str,
    sequence: int,
    epoch_ms: int,
    observables: list[tuple[int, int, int, int]],
) -> bytes:
    payload = bytearray()
    payload += struct.pack(">H", 1077)
    payload += struct.pack(">H", station_id)
    mp = mountpoint.encode("utf-8")
    payload.append(len(mp))
    payload += mp
    payload += struct.pack(">I", sequence)
    payload += struct.pack(">Q", epoch_ms)
    payload.append(len(observables))
    for sv_id, scale_exp, range_raw, phase_raw in observables:
        payload.append(sv_id)
        payload.append(scale_exp & 0xFF)
        payload += struct.pack(">I", range_raw)
        payload += struct.pack(">I", phase_raw)
    length = len(payload)
    frame = bytearray([0xD3, (length >> 8) & 0x03, length & 0xFF])
    frame += payload
    crc = crc24q(bytes(frame))
    frame += bytes([(crc >> 16) & 0xFF, (crc >> 8) & 0xFF, crc & 0xFF])
    return bytes(frame)


def corrupt_crc(frame: bytes) -> bytes:
    data = bytearray(frame)
    data[-1] ^= 0x01
    return bytes(data)


def reference_observable_sum(observables: list[tuple[int, int, int, int]]) -> float:
    total = 0.0
    for _sv, scale_exp, range_raw, _phase in observables:
        divisor = 10 ** max(scale_exp, 0)
        total += range_raw / divisor
    return total


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _u32_wrapping_add(value: int, addend: int) -> int:
    return _u32(value + addend)


def _u32_wrapping_sub(value: int, subtrahend: int) -> int:
    return _u32(value - subtrahend)


def reference_gap_delta(last_seq: int, next_seq: int) -> int:
    last = _u32(last_seq)
    nxt = _u32(next_seq)
    if nxt > last:
        diff = nxt - last
    else:
        diff = _u32_wrapping_sub(nxt, _u32_wrapping_add(last, 1)) + 1
    return 0 if diff <= 1 else diff - 1


def reference_station_chain_digest(db_path: Path) -> str:
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT event_id, station_key, action, created_at
            FROM station_audit
            ORDER BY created_at ASC, event_id ASC
            """
        ).fetchall()
    events = [
        {
            "event_id": r[0],
            "station_key": r[1],
            "action": r[2],
            "created_at": r[3],
        }
        for r in rows
    ]
    body = json.dumps(events, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def db_fingerprint(db_path: Path) -> str:
    return hashlib.sha256(db_path.read_bytes()).hexdigest()


def reference_seal_digest(seal: dict) -> str:
    body = json.dumps(
        {
            "db_fingerprint": seal["db_fingerprint"],
            "db_path": seal["db_path"],
            "event_count": seal["event_count"],
            "ledger_chain_digest": seal["ledger_chain_digest"],
            "tail_created_at": seal["tail_created_at"],
        },
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest()


def reference_staging_keys_digest(keys: list[str]) -> str:
    sorted_keys = sorted(set(keys))
    body = "\n".join(sorted_keys)
    return hashlib.sha256(body.encode()).hexdigest()


def reference_staging_keys_digest_insertion_order(keys: list[str]) -> str:
    body = "\n".join(keys)
    return hashlib.sha256(body.encode()).hexdigest()
