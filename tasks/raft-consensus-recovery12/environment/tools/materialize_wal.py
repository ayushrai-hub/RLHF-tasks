#!/usr/bin/env python3
"""Materialize wal_frames.bin from wal_entries.jsonl for Docker build."""
from __future__ import annotations

import base64
import gzip
import json
import struct
import sys
from pathlib import Path

import brotli


def decode_line(raw: str) -> dict:
    parsed = json.loads(raw)
    if not (isinstance(parsed, dict) and parsed.get("encoding") and parsed.get("payload")):
        return parsed
    payload = base64.b64decode(str(parsed["payload"]))
    if parsed["encoding"] == "base64+gzip+json":
        payload = gzip.decompress(payload)
    elif parsed["encoding"] == "base64+brotli+json":
        payload = brotli.decompress(payload)
    elif parsed["encoding"] != "base64+json":
        raise ValueError(f"unsupported WAL wrapper: {parsed['encoding']}")
    return json.loads(payload.decode("utf-8"))


def main() -> None:
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    commands = []
    for line in src.read_text(encoding="utf-8").splitlines():
        if line.strip():
            commands.append(decode_line(line))
    commands.sort(key=lambda c: (int(c["tick"]), int(c["index"]), str(c["node_id"])))
    payload = bytearray()
    for command in commands:
        data = json.dumps(command, sort_keys=True, separators=(",", ":")).encode()
        payload.extend(struct.pack(">I", len(data)))
        payload.extend(data)
    dst.write_bytes(bytes(payload))


if __name__ == "__main__":
    main()
