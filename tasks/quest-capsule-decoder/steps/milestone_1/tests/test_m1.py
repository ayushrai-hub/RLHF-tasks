"""Milestone 1: the loader decodes each capsule header from its base64 field."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import qcref  # noqa: E402

APP_DIR = os.environ.get("QCAP_APP_DIR", "/app")
OUT = os.path.join(APP_DIR, "out")


def run_decode(name):
    r = subprocess.run(
        ["php", os.path.join(APP_DIR, "bin", "qcap.php"), "decode", name],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"decode {name} failed: {r.stderr}"
    path = os.path.join(OUT, name + ".header.json")
    assert os.path.isfile(path), f"missing header artifact for {name}"
    with open(path) as fh:
        return json.load(fh)


class TestMilestone1:
    """Verify the decoded header matches the capsule's true parameters."""

    def test_entry_and_room_count(self):
        """entry and room_count decode from the glyph-encoded header fields."""
        for name in qcref.capsules():
            got = run_decode(name)
            exp = qcref.parse_header(name)
            assert got["entry"] == exp["entry"], name
            assert got["room_count"] == exp["room_count"], name

    def test_glyph_table_and_seed_base(self):
        """The plain glyph-set id and the glyph-encoded seed base are recovered."""
        for name in qcref.capsules():
            got = run_decode(name)
            exp = qcref.parse_header(name)
            assert got["glyph_table"] == exp["glyph_table"], name
            assert got["seed_base"] == exp["seed_base"], name

    def test_checksum_value_and_validity(self):
        """The check field decodes and validates as (entry + room_count + seed_base) mod 9973."""
        for name in qcref.capsules():
            got = run_decode(name)
            exp = qcref.parse_header(name)
            assert got["checksum"] == exp["checksum"], name
            assert got["checksum_ok"] is True, name

    def test_entry_matches_entry_room(self):
        """The decoded entry id is the room marked entry in the cartridge."""
        import sqlite3
        con = sqlite3.connect(qcref._db())
        try:
            for name in qcref.capsules():
                got = run_decode(name)
                row = con.execute(
                    "SELECT room_id FROM rooms WHERE capsule = ? AND kind = 'entry'", (name,)
                ).fetchone()
                assert row is not None and got["entry"] == row[0], name
        finally:
            con.close()

    def test_room_count_matches_rows(self):
        """The decoded room_count equals the number of room rows for the capsule."""
        import sqlite3
        con = sqlite3.connect(qcref._db())
        try:
            for name in qcref.capsules():
                got = run_decode(name)
                n = con.execute(
                    "SELECT COUNT(*) FROM rooms WHERE capsule = ?", (name,)
                ).fetchone()[0]
                assert got["room_count"] == n, name
        finally:
            con.close()
