"""Verifier tests for GlyphVault Terraform puzzle analyzer."""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

ENV_ROOT = Path("/app/environment")
ANALYZE = ENV_ROOT / "bin" / "puzzle-analyze"
TRANSCRIPT = ENV_ROOT / "artifacts" / "solve_transcript.json"
DB = ENV_ROOT / "data" / "puzzle.sqlite"
FIXTURES = Path("/tests/fixtures")


def _run_analyze() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ANALYZE)],
        cwd=ENV_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _load_transcript() -> dict:
    return json.loads(TRANSCRIPT.read_text(encoding="utf-8"))


def _db_score() -> tuple[int, str]:
    con = sqlite3.connect(DB)
    row = con.execute(
        "SELECT final_score, current_room FROM puzzle_state WHERE id = 1"
    ).fetchone()
    con.close()
    assert row is not None
    return int(row[0]), str(row[1])


def test_analyze_exit_zero() -> None:
    proc = _run_analyze()
    assert proc.returncode == 0, proc.stderr


def test_transcript_exists() -> None:
    assert TRANSCRIPT.is_file()


def test_final_room_is_vault() -> None:
    data = _load_transcript()
    assert data["final_room"] == "vault"


def test_final_score_matches_golden() -> None:
    golden = json.loads((FIXTURES / "score.golden.json").read_text(encoding="utf-8"))
    data = _load_transcript()
    assert data["final_score"] == golden["final_score"]


def test_sqlite_score_matches_transcript() -> None:
    data = _load_transcript()
    score, room = _db_score()
    assert score == data["final_score"]
    assert room == data["final_room"]


def test_rooms_visited_sequence() -> None:
    golden = json.loads((FIXTURES / "transcript.golden.json").read_text(encoding="utf-8"))
    data = _load_transcript()
    assert data["rooms_visited"] == golden["rooms_visited"]


def test_moves_applied_match_solver_script() -> None:
    golden = json.loads((FIXTURES / "transcript.golden.json").read_text(encoding="utf-8"))
    data = _load_transcript()
    assert data["moves_applied"] == golden["moves_applied"]


def test_glyphs_rendered_count() -> None:
    golden = json.loads((FIXTURES / "transcript.golden.json").read_text(encoding="utf-8"))
    data = _load_transcript()
    assert len(data["glyphs_rendered"]) == len(golden["glyphs_rendered"])


def test_glyph_characters_match_atlas() -> None:
    golden = json.loads((FIXTURES / "transcript.golden.json").read_text(encoding="utf-8"))
    data = _load_transcript()
    for got, exp in zip(data["glyphs_rendered"], golden["glyphs_rendered"]):
        assert got["char"] == exp["char"]
        assert got["glyph_id"] == exp["glyph_id"]
        assert got["atlas_col"] == exp["atlas_col"]
        assert got["atlas_row"] == exp["atlas_row"]


def test_transcript_key_order() -> None:
    raw = TRANSCRIPT.read_text(encoding="utf-8")
    rooms_pos = raw.index('"rooms_visited"')
    glyphs_pos = raw.index('"glyphs_rendered"')
    assert rooms_pos < glyphs_pos


def test_has_key_true() -> None:
    data = _load_transcript()
    assert data["has_key"] is True


def test_room_exits_table_used_not_hardcoded() -> None:
    """Garden must be reachable — broken hard-coded map cannot reach vault."""
    data = _load_transcript()
    assert "garden" in data["rooms_visited"]
    assert "crypt" in data["rooms_visited"]


def test_clue_blob_table_room_clues() -> None:
    """If clues table were used, glyph chars would be wrong."""
    data = _load_transcript()
    entry_glyph = next(g for g in data["glyphs_rendered"] if g["room"] == "entry")
    assert entry_glyph["char"] == "@"


def test_novel_probe_moves(tmp_path: Path) -> None:
    moves = tmp_path / "probe.moves"
    moves.write_text("GO east\nGO north\n", encoding="utf-8")
    proc = subprocess.run(
        [
            str(ENV_ROOT / "build" / "glyphvault_analyze"),
            "--db",
            str(DB),
            "--atlas",
            str(ENV_ROOT / "media" / "glyphs.png"),
            "--moves",
            str(moves),
            "--out",
            str(tmp_path / "probe.json"),
            "--terraform",
            str(ENV_ROOT / "terraform"),
        ],
        cwd=ENV_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads((tmp_path / "probe.json").read_text(encoding="utf-8"))
    assert payload["final_room"] == "library"
    assert payload["rooms_visited"] == ["entry", "hall", "library"]


def test_crlf_moves_trimmed(tmp_path: Path) -> None:
    moves = tmp_path / "crlf.moves"
    moves.write_bytes(b"GO east\r\nGO north\r\n")
    out = tmp_path / "crlf.json"
    proc = subprocess.run(
        [
            str(ENV_ROOT / "build" / "glyphvault_analyze"),
            "--db",
            str(DB),
            "--atlas",
            str(ENV_ROOT / "media" / "glyphs.png"),
            "--moves",
            str(moves),
            "--out",
            str(out),
            "--terraform",
            str(ENV_ROOT / "terraform"),
        ],
        cwd=ENV_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["moves_applied"] == ["GO east", "GO north"]


def test_unlock_requires_key(tmp_path: Path) -> None:
    moves = tmp_path / "nokey.moves"
    moves.write_text(
        "GO east\nGO north\nGO east\nGO north\nUNLOCK east\nGO east\n",
        encoding="utf-8",
    )
    out = tmp_path / "nokey.json"
    proc = subprocess.run(
        [
            str(ENV_ROOT / "build" / "glyphvault_analyze"),
            "--db",
            str(DB),
            "--atlas",
            str(ENV_ROOT / "media" / "glyphs.png"),
            "--moves",
            str(moves),
            "--out",
            str(out),
            "--terraform",
            str(ENV_ROOT / "terraform"),
        ],
        cwd=ENV_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
