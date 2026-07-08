"""Reference digest helpers mirroring runtime and verifier contracts."""

from __future__ import annotations

import hashlib
import zlib


def chain_fingerprint(rows: list[dict]) -> str:
    parts = [
        f"{r['scenario']},{r['view']},{r['principal']},{r['label']},{r['generation']}"
        for r in rows
    ]
    parts.sort()
    payload = "\n".join(parts) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def wal_crc(payload: str) -> int:
    return zlib.crc32(payload.encode("utf-8")) & 0xFFFFFFFF
