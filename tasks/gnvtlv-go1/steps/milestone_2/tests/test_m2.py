"""Tests for milestone 2. Run alone with: pytest tests/test_m2.py"""

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


def _run(sub: str, fixture: str) -> dict:
    _build()
    proc = subprocess.run(
        [str(BIN), sub, "--in", str(APP / "testdata" / fixture)],
        cwd=APP, capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"{sub} {fixture} failed: {proc.stderr}"
    return json.loads(proc.stdout)


class TestMilestone2:
    """Tests for milestone 2: IANA registry resolution and length-mismatch issues."""

    def test_milestone_1_artifact_persists(self) -> None:
        """`go test ./internal/decode/...` still passes (milestone 1 still green)."""
        proc = subprocess.run(
            ["go", "test", "./internal/decode/...", "./internal/wire/..."],
            cwd=APP, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"milestone-1 packages regressed:\n{proc.stdout}\n{proc.stderr}"

    def test_resolve_tests_pass(self) -> None:
        """`go test ./internal/resolve/...` exits 0."""
        proc = subprocess.run(
            ["go", "test", "./internal/resolve/..."],
            cwd=APP, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"resolve tests failed:\n{proc.stdout}\n{proc.stderr}"

    def test_known_options_recognized(self) -> None:
        """Known (class, type) pairs come back recognized with the registry name."""
        out = _run("resolve", "two_clean.bin")
        opts = out["options"]
        assert len(opts) == 2
        for o in opts:
            assert o["recognized"] is True, o
            assert o["name"] != "", o
            assert o["kind"] in {"u32", "u128", "struct", "varbin", "opaque"}, o

    def test_known_kind_dispatch_populates_decoded(self) -> None:
        """The decoded payload object is populated per the registry kind."""
        out = _run("resolve", "two_clean.bin")
        opt0, opt1 = out["options"]
        # opt0: u32, value 0xCAFEBABE = 3405691582
        assert opt0["kind"] == "u32", opt0
        assert opt0["decoded"] == 0xCAFEBABE, opt0
        # opt1: u128, payload all zeroes → hex string of 32 zero chars
        assert opt1["kind"] == "u128", opt1
        assert opt1["decoded"] == "0" * 32, opt1

    def test_unknown_option_marked_unrecognized(self) -> None:
        """Unknown (class, type) pairs come back recognized=false, kind=unknown."""
        out = _run("resolve", "unknown_crit.bin")
        opts = out["options"]
        assert len(opts) == 1
        assert opts[0]["recognized"] is False
        assert opts[0]["kind"] == "unknown"
        assert opts[0]["name"] == ""

    def test_protocol_type_name_filled(self) -> None:
        """Header.protocol_type_name comes from the Ethertype registry."""
        out = _run("resolve", "two_clean.bin")
        assert out["header"]["protocol_type"] == 25944
        assert out["header"]["protocol_type_name"] == "TransparentEthBridging"

    def test_length_mismatch_issue_emitted(self) -> None:
        """A fixed-size kind with wrong payload length produces OPT_LENGTH_MISMATCH on the right option."""
        out = _run("resolve", "length_mismatch.bin")
        issues = [i for i in out["issues"] if i["code"] == "OPT_LENGTH_MISMATCH"]
        assert len(issues) == 1, out
        assert issues[0]["opt_index"] == 0, issues[0]
        assert "message" in issues[0] and issues[0]["message"] != "", issues[0]

    def test_clean_packet_has_no_issues(self) -> None:
        """A clean packet emits no resolver issues."""
        out = _run("resolve", "two_clean.bin")
        assert out["issues"] == [], out

    def test_decode_errors_propagate_through_resolve(self) -> None:
        """If decode reports an error, resolve carries it in decode_errors."""
        out = _run("resolve", "rbits_nonzero.bin")
        codes = [e["code"] for e in out["decode_errors"]]
        assert "OPT_R_BITS_NONZERO" in codes, out

    def test_decoded_is_correct_type_per_kind(self) -> None:
        """u32 kind decodes to a JSON integer, u128 to a hex string."""
        out = _run("resolve", "two_clean.bin")
        opt0, opt1 = out["options"]
        assert isinstance(opt0["decoded"], int) and not isinstance(opt0["decoded"], bool), opt0
        assert isinstance(opt1["decoded"], str), opt1

    def test_unknown_decoded_is_null(self) -> None:
        """Unknown options leave decoded as null."""
        out = _run("resolve", "unknown_crit.bin")
        assert out["options"][0]["decoded"] is None, out

    def test_struct_kind_decoded_populates_tag_and_tail(self) -> None:
        """The struct kind decodes into an object with `tag` (u32) and `tail_hex` (string)."""
        out = _run("resolve", "kinds_dispatch.bin")
        struct_opts = [o for o in out["options"] if o["kind"] == "struct"]
        assert len(struct_opts) == 1, out
        opt = struct_opts[0]
        assert opt["recognized"] is True, opt
        assert opt["name"] == "vendor-policy-tag", opt
        assert isinstance(opt["decoded"], dict), opt
        assert opt["decoded"]["tag"] == 0xCAFEBABE, opt
        assert opt["decoded"]["tail_hex"] == "01020304", opt

    def test_varbin_kind_decoded_to_hex_string(self) -> None:
        """The varbin kind decodes into a lowercase hex string of the payload."""
        out = _run("resolve", "kinds_dispatch.bin")
        varbin_opts = [o for o in out["options"] if o["kind"] == "varbin"]
        assert len(varbin_opts) == 1, out
        opt = varbin_opts[0]
        assert opt["recognized"] is True, opt
        assert opt["name"] == "vendor-trace-id", opt
        assert isinstance(opt["decoded"], str), opt
        assert opt["decoded"] == "aabbccdd", opt

    def test_opaque_kind_decoded_to_hex_string(self) -> None:
        """The opaque kind decodes into a lowercase hex string of the payload."""
        out = _run("resolve", "kinds_dispatch.bin")
        opaque_opts = [o for o in out["options"] if o["kind"] == "opaque"]
        assert len(opaque_opts) == 1, out
        opt = opaque_opts[0]
        assert opt["recognized"] is True, opt
        assert opt["name"] == "exp-classifier", opt
        assert isinstance(opt["decoded"], str), opt
        assert opt["decoded"] == "11223344", opt

    def test_unregistered_protocol_type_name_is_empty(self) -> None:
        """An unregistered protocol_type yields an empty `protocol_type_name`."""
        out = _run("resolve", "unregistered_ether.bin")
        assert out["header"]["protocol_type"] == 0x9999, out["header"]
        assert out["header"]["protocol_type_name"] == "", out["header"]
