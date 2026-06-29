"""Milestone 3 -- Integrate Terminal Expedition.

The agent must extend the C engine so that
``relicvault --replay --pack <vault.pack> --script <file> --out <file>`` replays a
scripted expedition and writes the transcript (Appendix IV). The headline
transcript at /app/out/transcript.txt is checked against an independent reference
simulator, and the freshly built binary is additionally driven on disjoint
synthetic pack+script pairs (an ALIVE run and a DOWNED run) -- so the only way to
pass is a real, rule-correct engine, not a transcribed answer.

Run alone with: pytest /tests/test_m3.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import relic_ref as R  # noqa: E402

ARCHIVE = "/app/archive"
OUT = Path("/app/out")
TRANSCRIPT = OUT / "transcript.txt"
PACK = OUT / "vault.pack"
ENGINE_SRC = Path("/app/engine/relicvault.c")
ENGINE_BIN = Path("/app/engine/relicvault")

# Synthetic expedition scripts driven against the synthetic pack (unseen data).
ALIVE_SCRIPT = [
    "ADVANCE", "STRIKE", "STRIKE", "STRIKE", "GRAB", "STRIKE",   # ch0: SLAIN, CLAIM, EMPTY
    "ADVANCE", "STRIKE", "STRIKE", "STRIKE", "GRAB",             # ch1: SLAIN, WARDED (no relic)
    "ADVANCE", "STRIKE", "STRIKE", "GRAB", "GRAB", "BRACE",      # ch2: SLAIN, CLAIM, WARDED (taken), BRACE
    "ADVANCE", "GRAB", "BRACE",                                  # ch3: WARDED (guardian alive), BRACE
    "ADVANCE", "GRAB", "STRIKE",                                 # ch4: CLAIM, EMPTY (no guardian)
    "ADVANCE",                                                   # EDGE (already at last chamber)
]
DOWNED_SCRIPT = [
    "ADVANCE", "ADVANCE", "ADVANCE", "ADVANCE",
    "STRIKE", "STRIKE", "STRIKE", "GRAB", "ADVANCE",
]


def _replay(pack_bytes, script_lines):
    """Run the agent's compiled engine on a pack + script, return its transcript."""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "syn.pack"
        s = Path(tmp) / "syn.script"
        o = Path(tmp) / "syn.txt"
        p.write_bytes(pack_bytes)
        s.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
        proc = subprocess.run(
            [str(ENGINE_BIN), "--replay", "--pack", str(p),
             "--script", str(s), "--out", str(o)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, (
            f"engine failed (rc={proc.returncode}) STDERR:\n{proc.stderr}"
        )
        return o.read_bytes()


class TestMilestone3:
    """Tests for milestone 3: the scripted terminal expedition."""

    def test_earlier_artifacts_persist(self) -> None:
        """vault.pack (milestone 2) must still exist (state persists)."""
        assert PACK.exists(), "vault.pack is missing -- was milestone 2 completed?"

    def test_engine_is_real_c(self) -> None:
        """A non-trivial C source and a compiled ELF executable must exist, so
        the transcript cannot be produced by a non-C shortcut."""
        assert ENGINE_SRC.exists(), f"{ENGINE_SRC} is missing"
        assert len(ENGINE_SRC.read_text().splitlines()) > 50, (
            "relicvault.c is too small to be the real engine"
        )
        assert ENGINE_BIN.exists(), f"{ENGINE_BIN} was not built"
        assert os.access(ENGINE_BIN, os.X_OK), f"{ENGINE_BIN} is not executable"
        assert ENGINE_BIN.read_bytes()[:4] == b"\x7fELF", (
            f"{ENGINE_BIN} is not a native ELF binary"
        )

    def test_headline_transcript_exists(self) -> None:
        """The engine must write /app/out/transcript.txt."""
        assert TRANSCRIPT.exists(), f"{TRANSCRIPT} was not produced"

    def test_headline_transcript_matches_reference(self) -> None:
        """The shipped expedition transcript must match the independent
        reference simulation byte-for-byte (Appendix IV)."""
        ref_pack = R.pack_bytes(R.build_chambers(R.read_archive(ARCHIVE)))
        script = Path(f"{ARCHIVE}/expedition.script").read_text().splitlines()
        expected = R.simulate(R.parse_pack(ref_pack), script)
        assert TRANSCRIPT.read_bytes() == expected, (
            "transcript.txt does not match the canonical expedition"
        )

    def test_engine_on_synthetic_alive_run(self) -> None:
        """The built engine, run on an unseen synthetic vault, must reproduce the
        reference transcript for an expedition the delver survives (covers
        SLAIN, CLAIM, WARDED, BRACE, EMPTY, EDGE)."""
        chambers = R.build_chambers(R.synthetic_tables())
        pack = R.pack_bytes(chambers)
        produced = _replay(pack, ALIVE_SCRIPT)
        expected = R.simulate(R.parse_pack(pack), ALIVE_SCRIPT)
        assert produced == expected, "engine disagrees with reference (alive run)"

    def test_engine_on_synthetic_downed_run(self) -> None:
        """The built engine, run on an unseen synthetic vault, must reproduce the
        reference transcript for an expedition the delver loses, halting at the
        DOWNED line and ignoring the rest of the script."""
        chambers = R.build_chambers(R.synthetic_tables())
        pack = R.pack_bytes(chambers)
        produced = _replay(pack, DOWNED_SCRIPT)
        expected = R.simulate(R.parse_pack(pack), DOWNED_SCRIPT)
        assert produced == expected, "engine disagrees with reference (downed run)"
