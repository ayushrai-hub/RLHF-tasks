"""Tests for milestone 1. Run alone with: pytest tests/test_m1.py"""

import json
import subprocess
from pathlib import Path


APP = Path("/app")
BIN = APP / "bin" / "gnvtlv"


def _build():
    BIN.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["go", "build", "-o", str(BIN), "./cmd/gnvtlv"],
        cwd=APP, capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"go build failed:\n{proc.stdout}\n{proc.stderr}"


def _run_decode(fixture: str) -> dict:
    _build()
    proc = subprocess.run(
        [str(BIN), "decode", "--in", str(APP / "testdata" / fixture)],
        cwd=APP, capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"decode {fixture} failed: {proc.stderr}"
    return json.loads(proc.stdout)


class TestMilestone1:
    """Tests for milestone 1: wire-level decoder green, R-bits strictness wired."""

    def test_module_builds(self) -> None:
        """`go build ./...` exits 0."""
        proc = subprocess.run(
            ["go", "build", "./..."],
            cwd=APP, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"go build failed:\n{proc.stdout}\n{proc.stderr}"

    def test_wire_tests_pass(self) -> None:
        """`go test ./internal/wire/...` exits 0."""
        proc = subprocess.run(
            ["go", "test", "./internal/wire/..."],
            cwd=APP, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"wire tests failed:\n{proc.stdout}\n{proc.stderr}"

    def test_decode_tests_pass(self) -> None:
        """`go test ./internal/decode/...` exits 0."""
        proc = subprocess.run(
            ["go", "test", "./internal/decode/..."],
            cwd=APP, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"decode tests failed:\n{proc.stdout}\n{proc.stderr}"

    def test_bare_header_decodes_clean(self) -> None:
        """An 8-byte packet with OptLen=0 decodes to no options and no errors."""
        out = _run_decode("bare_header.bin")
        assert out["header"]["opt_len_words"] == 0
        assert out["options"] == []
        assert out["errors"] == []
        assert isinstance(out["outer_bytes"], int) and out["outer_bytes"] == 8
        assert isinstance(out["inner_bytes"], int) and out["inner_bytes"] == 0

    def test_two_clean_options_lengths_match_wire(self) -> None:
        """Two-clean fixture exposes correctly aligned option lengths."""
        out = _run_decode("two_clean.bin")
        opts = out["options"]
        assert len(opts) == 2, opts
        # Option 0: u32 → length_words=1, length_bytes=4
        assert opts[0]["length_words"] == 1, opts[0]
        assert opts[0]["length_bytes"] == 4, opts[0]
        assert opts[0]["opt_class"] == 0x0103
        assert opts[0]["type"] == 5
        # Option 1: u128 → length_words=4, length_bytes=16
        assert opts[1]["length_words"] == 4, opts[1]
        assert opts[1]["length_bytes"] == 16, opts[1]
        assert opts[1]["opt_class"] == 0x0103
        assert opts[1]["type"] == 6
        assert out["errors"] == []

    def test_two_clean_offsets_walk_correctly(self) -> None:
        """Per-option offset_bytes walks 8 → 8+8 = 16 across the fixture."""
        out = _run_decode("two_clean.bin")
        opts = out["options"]
        # opt 0 starts at byte 8 (right after fixed header).
        assert opts[0]["offset_bytes"] == 8, opts[0]
        # opt 1 starts at 8 + (4 + 4) = 16.
        assert opts[1]["offset_bytes"] == 16, opts[1]

    def test_r_bits_nonzero_reported(self) -> None:
        """A packet with nonzero R bits emits OPT_R_BITS_NONZERO."""
        out = _run_decode("rbits_nonzero.bin")
        codes = [e["code"] for e in out["errors"]]
        assert "OPT_R_BITS_NONZERO" in codes, out

    def test_r_bits_value_preserved_on_option(self) -> None:
        """The decoded option carries the actual R bits value (5)."""
        out = _run_decode("rbits_nonzero.bin")
        assert len(out["options"]) == 1
        assert out["options"][0]["r_bits"] == 5, out["options"][0]

    def test_clean_packet_has_no_r_bits_error(self) -> None:
        """A clean packet does NOT emit OPT_R_BITS_NONZERO."""
        out = _run_decode("two_clean.bin")
        codes = [e["code"] for e in out["errors"]]
        assert "OPT_R_BITS_NONZERO" not in codes, out

    def test_version_nonzero_reported(self) -> None:
        """A packet with Version=1 emits VERSION_NONZERO."""
        out = _run_decode("version_one.bin")
        codes = [e["code"] for e in out["errors"]]
        assert "VERSION_NONZERO" in codes, out

    def test_opt_len_overrun_reported(self) -> None:
        """When OptLen exceeds available bytes, OPT_LEN_OVERRUN fires."""
        out = _run_decode("opt_len_overrun.bin")
        codes = [e["code"] for e in out["errors"]]
        assert "OPT_LEN_OVERRUN" in codes, out

    def test_length_fields_are_ints_not_floats(self) -> None:
        """Length fields are JSON integers, not floats."""
        out = _run_decode("two_clean.bin")
        for o in out["options"]:
            assert isinstance(o["length_words"], int) and not isinstance(o["length_words"], bool)
            assert isinstance(o["length_bytes"], int) and not isinstance(o["length_bytes"], bool)
            assert isinstance(o["opt_class"], int)
            assert isinstance(o["type"], int)

    def test_empty_arrays_serialise_as_brackets(self) -> None:
        """An empty options array is `[]`, not `null`."""
        bare = _run_decode("bare_header.bin")
        # The bytes of the rendered JSON must contain `"options": []`.
        proc = subprocess.run(
            [str(BIN), "decode", "--in", str(APP / "testdata" / "bare_header.bin")],
            cwd=APP, capture_output=True, text=True, check=True,
        )
        assert '"options": []' in proc.stdout, proc.stdout
        # And the same for errors.
        assert '"errors": []' in proc.stdout, proc.stdout
        assert bare["options"] == []
        assert bare["errors"] == []
