import csv
import io
import json
import tomllib
from pathlib import Path


def _normalize_text(raw: str) -> str:
    """Replace literal two-character \\n sequences with real newlines."""
    return raw.replace("\\n", "\n")


def load_csv(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    normalized = _normalize_text(raw)
    return list(csv.DictReader(io.StringIO(normalized)))


def load_toml_text(path: Path) -> dict:
    raw = path.read_bytes()
    normalized = raw.replace(b"\\n", b"\n")
    return tomllib.loads(normalized.decode("utf-8"))


def load_lines(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    normalized = _normalize_text(raw)
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
