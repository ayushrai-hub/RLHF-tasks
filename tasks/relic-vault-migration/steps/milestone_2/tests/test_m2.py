"""Milestone 2 -- Migrate Puzzle Database.

The agent must complete the harness so that
``python /app/harness/migrate.py pack --archive <dir> --out <dir>`` writes the
little-endian ``vault.pack`` image (Appendices II-III). The derived chamber
statistics combine the room biome, the guardian, the relic, and the tile hazard
count, so getting any rule wrong changes the bytes. Ground truth is recomputed
from the raw archive, and the harness is additionally driven on a disjoint
synthetic archive.

Run alone with: pytest /tests/test_m2.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import relic_ref as R  # noqa: E402

ARCHIVE = "/app/archive"
PACK = Path("/app/out/vault.pack")
CONSULTED = Path("/app/out/consulted.json")
REPORT = Path("/app/out/schema_report.json")


def _run_harness(command, archive, out):
    """Invoke the agent's harness; raise with captured output on failure."""
    proc = subprocess.run(
        [sys.executable, "/app/harness/migrate.py", command,
         "--archive", archive, "--out", out],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        f"migrate.py {command} failed (rc={proc.returncode})\n"
        f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )


class TestMilestone2:
    """Tests for milestone 2: the migrated vault.pack database image."""

    def test_milestone_1_artifact_persists(self) -> None:
        """Milestone 1's schema report must still exist (state persists)."""
        assert REPORT.exists(), (
            "schema_report.json is missing -- was milestone 1 completed?"
        )

    def test_pack_exists(self) -> None:
        """The harness must write /app/out/vault.pack."""
        assert PACK.exists(), f"{PACK} was not produced by the harness"

    def test_pack_header_and_footer(self) -> None:
        """The image must carry the RVP1 magic, a correct chamber count, and the
        RVPE footer (Appendix III)."""
        data = PACK.read_bytes()
        assert data[:4] == b"RVP1", "missing RVP1 magic header"
        assert data[-4:] == b"RVPE", "missing RVPE footer"
        chambers = R.parse_pack(data)
        expected = R.build_chambers(R.read_archive(ARCHIVE))
        assert len(chambers) == len(expected), "chamber count mismatch"

    def test_chambers_ordered_by_depth_with_derived_stats(self) -> None:
        """Chambers must be ordered by depth and carry the exact derived
        guard_hp / guard_atk / relic_worth values from Appendix II."""
        chambers = R.parse_pack(PACK.read_bytes())
        expected = R.build_chambers(R.read_archive(ARCHIVE))
        for got, exp in zip(chambers, expected):
            for field in ("room_id", "chamber_index", "guard_hp", "guard_atk",
                          "relic_worth", "hazard", "biome_code", "sigil",
                          "name", "species"):
                assert got[field] == exp[field], (
                    f"chamber {exp['chamber_index']} field {field}: "
                    f"{got[field]!r} != {exp[field]!r}"
                )

    def test_pack_bytes_are_canonical(self) -> None:
        """The whole image must be byte-for-byte identical to the canonical
        migration of the raw archive."""
        expected = R.pack_bytes(R.build_chambers(R.read_archive(ARCHIVE)))
        assert PACK.read_bytes() == expected, (
            "vault.pack is not byte-identical to the canonical migration"
        )

    def test_consulted_manifest_exists(self) -> None:
        """The pack migration must also write /app/out/consulted.json (App. V)."""
        assert CONSULTED.exists(), (
            f"{CONSULTED} was not produced by the harness (Appendix V)"
        )

    def test_consulted_manifest_is_canonical(self) -> None:
        """consulted.json must be byte-identical to the canonical consulted-scope
        audit: every guardian/relic candidate EXAMINED for a chamber room
        (selected AND superseded), excluding orphans -- not the selected set, and
        not every record (Appendix V, Rule II.3)."""
        expected = R.consulted_manifest_bytes(R.read_archive(ARCHIVE))
        assert CONSULTED.read_bytes() == expected, (
            "consulted.json is not byte-identical to the canonical consulted scope"
        )

    def test_harness_on_synthetic_archive(self) -> None:
        """Driving the harness on a disjoint synthetic archive must yield the
        canonical pack AND consulted manifest for THAT data (anti-hardcode); the
        synthetic archive carries superseded candidates and orphans the agent
        never saw, so a 'selected-only' or 'everything' manifest cannot pass."""
        tables = R.synthetic_tables()
        expected_pack = R.pack_bytes(R.build_chambers(tables))
        expected_manifest = R.consulted_manifest_bytes(tables)
        with tempfile.TemporaryDirectory() as tmp:
            arc = Path(tmp) / "archive"
            out = Path(tmp) / "out"
            arc.mkdir()
            R.write_archive(arc, tables)
            _run_harness("pack", str(arc), str(out))
            produced_pack = (out / "vault.pack").read_bytes()
            produced_manifest = (out / "consulted.json").read_bytes()
        assert produced_pack == expected_pack, (
            "harness produced a non-canonical pack on synthetic input"
        )
        assert produced_manifest == expected_manifest, (
            "harness produced a non-canonical consulted.json on synthetic input"
        )
