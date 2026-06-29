"""Reference digest and R8 tolerance helpers mirroring runtime contracts."""

from __future__ import annotations

import hashlib
import json
import zlib

R8_NARROW_EPS = 1e-9


def narrow_block_rms(generation: int, action_code: int) -> float:
  return generation * 1e-4 + action_code * 1e-5


def t9_narrow_ok(observed: float, generation: int, action_code: int) -> bool:
  expected = narrow_block_rms(generation, action_code)
  return abs(observed - expected) <= R8_NARROW_EPS


def body_digest(rows: list[dict]) -> str:
  sorted_rows = sorted(
      rows,
      key=lambda r: (
          r["scenario"],
          r["view"],
          r["principal"],
          r["label"],
          r["generation"],
      ),
  )
  canonical = json.dumps(sorted_rows, sort_keys=True, separators=(",", ":"))
  return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def wal_crc(payload: str) -> int:
  return zlib.crc32(payload.encode("utf-8")) & 0xFFFFFFFF
