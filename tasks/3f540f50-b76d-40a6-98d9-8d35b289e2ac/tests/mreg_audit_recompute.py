#!/usr/bin/env python3
"""Independent register capture audit recomputation for verifier cross-checks."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ALLOWLIST = Path("/app/environment/data/slave_allowlist.txt")


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


def parse_frames(blob: bytes) -> tuple[list[dict], int]:
    off = 0
    frames: list[dict] = []
    crc_fails = 0
    while off < len(blob):
        if len(blob) - off < 20:
            raise ValueError("truncated frame")
        if blob[off : off + 4] != b"MREG":
            raise ValueError("bad magic")
        segment = blob[off + 4]
        profile = blob[off + 5]
        slave = blob[off + 6]
        func = blob[off + 7]
        reg = struct.unpack_from(">H", blob, off + 8)[0]
        count = struct.unpack_from(">H", blob, off + 10)[0]
        seq = struct.unpack_from(">I", blob, off + 12)[0]
        plen = struct.unpack_from(">H", blob, off + 16)[0]
        end = off + 18 + plen
        if end + 2 > len(blob):
            raise ValueError("truncated payload")
        body = blob[off:end]
        want = struct.unpack_from("<H", blob, end)[0]
        got = modbus_crc(body)
        if got != want:
            crc_fails += 1
            off = end + 2
            continue
        payload = blob[off + 18 : end]
        frames.append(
            {
                "segment": segment,
                "profile": profile,
                "slave": slave,
                "func": func,
                "reg": reg,
                "count": count,
                "seq": seq,
                "payload": payload,
            }
        )
        off = end + 2
    return frames, crc_fails


def list_mreg_files(directory: Path) -> list[str]:
    names = sorted(p.name for p in directory.iterdir() if p.suffix == ".mreg")
    order_path = directory / ".mregorder"
    if order_path.is_file():
        spec = json.loads(order_path.read_text(encoding="utf-8"))
        priority = spec.get("priority") or []
        have = set(names)
        ordered: list[str] = []
        seen: set[str] = set()
        for name in priority:
            if name not in have or name in seen:
                continue
            ordered.append(name)
            seen.add(name)
        for name in names:
            if name not in seen:
                ordered.append(name)
        return ordered
    return names


def load_allowlist(path: Path) -> set[int]:
    out: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(int(line))
    return out


def partition_checkpoints(frames: list[dict]) -> tuple[list[dict], int]:
    kept: list[dict] = []
    skips = 0
    for fr in frames:
        if fr["func"] == 0x00:
            skips += 1
            continue
        kept.append(fr)
    return kept, skips


def collapse_seq(frames: list[dict]) -> tuple[list[dict], int]:
    by_seq: dict[int, dict] = {}
    order: list[int] = []
    for fr in frames:
        seq = int(fr["seq"])
        if seq not in by_seq:
            order.append(seq)
        by_seq[seq] = fr
    collapsed = [by_seq[s] for s in order]
    return collapsed, len(frames) - len(collapsed)


def chain_root(frames: list[dict], seed: str = "") -> str:
    prev = seed or ("0" * 64)
    for fr in frames:
        if fr["func"] >= 0x80 or fr["func"] == 0x00:
            continue
        raw = bytes(fr["payload"])
        digest = hashlib.sha256(prev.encode() + b":" + raw).hexdigest()
        prev = digest
    return prev


def summarize_reg_span(frames: list[dict]) -> tuple[int, int]:
    regs = [int(fr["reg"]) for fr in frames if fr["func"] == 0x03]
    if not regs:
        return 0, 0
    return min(regs), max(regs)


def recompute(directory: Path, segment: int, tip_hex: str | None = None) -> dict:
    allowed = load_allowlist(ALLOWLIST)
    names = list_mreg_files(directory)
    frames: list[dict] = []
    crc_total = 0
    for name in names:
        blob = (directory / name).read_bytes()
        parsed, fails = parse_frames(blob)
        crc_total += fails
        frames.extend(parsed)

    frames, checkpoint_skips = partition_checkpoints(frames)
    segment_frames: list[dict] = []
    slave_rejects = 0
    for fr in frames:
        if int(fr["segment"]) != segment:
            continue
        if int(fr["slave"]) not in allowed:
            slave_rejects += 1
            continue
        segment_frames.append(fr)

    collapsed, drops = collapse_seq(segment_frames)
    seed = ""
    if (directory / ".mreg_continue").exists() and tip_hex:
        seed = tip_hex.strip()
    root = chain_root(collapsed, seed)

    reg_reads = 0
    exceptions = 0
    slaves: set[int] = set()
    for fr in collapsed:
        if fr["func"] == 0x03:
            reg_reads += int(fr["count"])
            slaves.add(int(fr["slave"]))
        if fr["func"] >= 0x80:
            exceptions += 1

    min_reg, max_reg = summarize_reg_span(collapsed)
    return {
        "api_version": 1,
        "segment": segment,
        "mreg_files": names,
        "frame_count": len(collapsed),
        "register_read_count": reg_reads,
        "crc_failure_count": crc_total,
        "exception_count": exceptions,
        "chain_root_hex": root,
        "duplicate_seq_drops": drops,
        "slave_reject_count": slave_rejects,
        "checkpoint_skip_count": checkpoint_skips,
        "min_reg": min_reg,
        "max_reg": max_reg,
        "active_slave_count": len(slaves),
    }


def main() -> None:
    if len(sys.argv) not in (3, 4):
        raise SystemExit("usage: mreg_audit_recompute.py <dir> <segment> [tip_hex]")
    directory = Path(sys.argv[1])
    segment = int(sys.argv[2])
    tip = sys.argv[3] if len(sys.argv) == 4 else None
    print(json.dumps(recompute(directory, segment, tip), indent=2))


if __name__ == "__main__":
    main()
