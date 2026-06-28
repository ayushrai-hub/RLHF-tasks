"""Shared reference helpers for depfix header closure and fixture checksums."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

APP = Path("/app")
INCLUDE = APP / "include"

TARGET_SOURCES: dict[str, list[str]] = {
    "depfix_hash": ["src/detail/hash_mix.cpp"],
    "depfix_core": ["src/core.cpp"],
    "depfix_util": ["src/util.cpp"],
    "depfix_app": ["src/main.cpp"],
}

INCLUDE_RE = re.compile(r'^\s*#include\s+"depfix/([^"]+)"\s*')


def _read_includes(path: Path) -> list[str]:
    if not path.is_file():
        return []
    headers: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = INCLUDE_RE.match(line)
        if match:
            headers.append(f"include/depfix/{match.group(1)}")
    return headers


def compute_header_closure(target: str) -> list[str]:
    """Return sorted project-relative header paths reachable from target sources."""
    seen: set[str] = set()
    queue: list[str] = []
    for rel_src in TARGET_SOURCES[target]:
        queue.extend(_read_includes(APP / rel_src))
    while queue:
        rel_hdr = queue.pop(0)
        if rel_hdr in seen:
            continue
        seen.add(rel_hdr)
        queue.extend(_read_includes(APP / rel_hdr))
    return sorted(seen)


def compute_depfile_digest(data_lines: list[str]) -> str:
    """SHA-256 of sorted data lines joined with trailing newline."""
    payload = "\n".join(data_lines) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_depfile(path: Path) -> tuple[list[str], dict[str, str]]:
    """Split depfile into data lines and footer key/value pairs."""
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    data: list[str] = []
    footer: dict[str, str] = {}
    for ln in lines:
        if ln.startswith("# depfix-lines="):
            footer["lines"] = ln.split("=", 1)[1]
        elif ln.startswith("# depfix-digest="):
            footer["digest"] = ln.split("=", 1)[1]
        elif ln.startswith("#"):
            continue
        else:
            data.append(ln)
    return data, footer


def sha256_tree(root: Path) -> str:
    """Deterministic SHA256 over relative file paths and contents under root."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def public_include_checksum() -> str:
    return sha256_tree(APP / "include" / "depfix")


def apply_touch_token(path: Path, token: str) -> None:
    """Append contract touch marker line to a header file."""
    path.write_text(
        path.read_text(encoding="utf-8") + f"\n// depfix-touch-token={token}\n",
        encoding="utf-8",
    )
