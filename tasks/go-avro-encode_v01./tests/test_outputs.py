"""Dynamic verifier for the Avro binary encoder.

The program is built from the agent's sources under /app/src and run against a
hidden battery built at grade time by avro_ref.build_battery(). For every case
the status and, on success, the exact hex of the Avro binary encoding must match
the reference encoder. The stable I/O harness, the struct/contract definitions,
and the schema parser are checked unchanged, and the source-file set is checked
exact, so the result reflects the encoder the agent wrote rather than a
hand-written output or an altered harness.
"""

import hashlib
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avro_ref  # noqa: E402

APP = "/app"
SRC = os.path.join(APP, "src")

EXPECTED_SRC = {
    "main.go", "types.go", "schema.go",
    "varint.go", "primitives.go", "complex.go", "encoder.go",
}

PINNED_SHA = {
    "main.go": "c79307450f492ac15b9310eeca2c36b0d8c705a383c777a3f68cf871bac9f380",
    "types.go": "e58ca837c75b0b1022a4a58802c70422ea54853f5618386954f331c4a957e1a1",
    "schema.go": "3374efc1f1dad063d145d5e3337a51a44a5527d601473ea286091786d85d29b3",
    "go.mod": "eff5e8ad562cf0d84fd4a12c8820baa9df75c4331e2e0b77b3fa3a9c9bbfe932",
}


def _norm_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def test_source_file_set_unchanged():
    """The Go source set under /app/src must be exactly the provided files; no
    files may be added, removed, or renamed."""
    present = {f for f in os.listdir(SRC) if f.endswith(".go")}
    assert present == EXPECTED_SRC, f"src set changed: {present ^ EXPECTED_SRC}"


def test_pinned_contract_files_unmodified():
    """The I/O harness, struct/contract definitions, and the schema parser are
    pinned and must be unchanged."""
    for name, want in PINNED_SHA.items():
        path = os.path.join(APP, "go.mod") if name == "go.mod" else os.path.join(SRC, name)
        assert os.path.exists(path), f"missing pinned file: {name}"
        assert _norm_sha(path) == want, f"pinned file was modified: {name}"


@pytest.fixture(scope="session")
def agent_bin(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("bin") / "avroencode")
    proc = subprocess.run(
        ["go", "build", "-o", out, "./src"],
        cwd=APP, capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"go build failed:\n{proc.stdout}\n{proc.stderr}"
    return out


def test_program_builds(agent_bin):
    """The encoder must build from the sources under /app/src."""
    assert os.path.exists(agent_bin)


def _run(binpath, inp):
    proc = subprocess.run([binpath], input=json.dumps(inp).encode(), capture_output=True)
    assert proc.returncode == 0, f"program exit {proc.returncode}: {proc.stderr.decode()[:400]}"
    return json.loads(proc.stdout.decode())


def test_encode_battery_matches_contract(agent_bin):
    """Encode the hidden battery and require an exact match on every case: the
    status and, on success, the hex of the Avro binary encoding."""
    inp, expected = avro_ref.build_battery()
    got = _run(agent_bin, inp)

    assert [c["id"] for c in got["cases"]] == [c["id"] for c in expected["cases"]], \
        "case set or order changed"

    mism = []
    for e, g in zip(expected["cases"], got["cases"]):
        if e != g:
            mism.append(f"{e['id']}:\n   expected {e}\n   got      {g}")
    assert not mism, "battery mismatch:\n" + "\n".join(mism[:8])
