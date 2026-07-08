"""Pytest helpers for milestone 2 native verifier repair."""

import csv
import ctypes
import subprocess
from pathlib import Path

from ledger_expected import (
    CHAIN_ROOT,
    compute_chain_root,
    expected_canonical_samples,
    forged_rows,
    load_fixture_rows,
)

LIB_PATH = Path("/app/native/libledger_verify.so")


def rebuild_library():
    """Rebuild the shared library from the agent-edited C source."""
    subprocess.run(["make", "-C", "/app/native", "-B"], check=True)
    assert LIB_PATH.is_file()


def load_lib():
    rebuild_library()
    lib = ctypes.CDLL(str(LIB_PATH))
    lib.ledger_canonicalize_row.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t]
    lib.ledger_canonicalize_row.restype = ctypes.c_int
    lib.ledger_verify_signature.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
    ]
    lib.ledger_verify_signature.restype = ctypes.c_int
    lib.ledger_row_digest.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t]
    lib.ledger_row_digest.restype = ctypes.c_int
    lib.ledger_compute_chain_root.argtypes = [
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.c_size_t,
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]
    lib.ledger_compute_chain_root.restype = ctypes.c_int
    return lib


def call_canonicalize(lib, csv_row: str) -> str:
    buf = ctypes.create_string_buffer(4096)
    rc = lib.ledger_canonicalize_row(csv_row.encode(), buf, len(buf))
    assert rc == 0, f"canonicalize failed for row: {csv_row}"
    return buf.value.decode()


def call_verify(lib, csv_row: str) -> int:
    parts = next(csv.reader([csv_row]))
    sig = parts[6]
    signer = parts[5]
    posted_at = parts[4]
    canonical = call_canonicalize(lib, csv_row)
    return lib.ledger_verify_signature(
        canonical.encode(),
        sig.encode(),
        signer.encode(),
        posted_at.encode(),
    )


class TestMilestone2:
    """Verify repaired native ledger verifier behavior."""

    def test_canonicalization_matches_fixture(self):
        """Canonical pipe payloads must match independently derived samples."""
        lib = load_lib()
        for seq, expected in expected_canonical_samples().items():
            row = next(",".join(r) for r in load_fixture_rows() if r[0] == seq)
            assert call_canonicalize(lib, row) == expected

    def test_valid_fixture_signatures_verify(self):
        """Every fixture row must pass native signature verification."""
        lib = load_lib()
        for row in load_fixture_rows():
            line = ",".join(row)
            assert call_verify(lib, line) == 0
            canonical = call_canonicalize(lib, line)
            tampered = canonical.replace("|", "!", 1)
            rc = lib.ledger_verify_signature(
                tampered.encode(),
                row[6].encode(),
                row[5].encode(),
                row[4].encode(),
            )
            assert rc != 0, "verifier must reject tampered canonical payloads"

    def test_forged_rows_rejected(self):
        """Tampered and out-of-policy rows must fail verification."""
        lib = load_lib()
        for csv_row, should_pass in forged_rows():
            if should_pass:
                continue
            assert call_verify(lib, csv_row) != 0

    def test_wrong_key_for_posted_at_rejected(self):
        """Rows must fail when the signer key does not match the posted_at rotation boundary."""
        lib = load_lib()
        row = load_fixture_rows()[0]
        tampered = row.copy()
        tampered[4] = "2026-03-05T00:00:00Z"
        assert call_verify(lib, ",".join(tampered)) != 0

    def test_chain_root_matches_independent_recompute(self):
        """Chain root must match SHA256 chain derived from fixture rows."""
        lib = load_lib()
        digests = []
        for row in load_fixture_rows():
            line = ",".join(row)
            canonical = call_canonicalize(lib, line)
            digest_buf = ctypes.create_string_buffer(128)
            rc = lib.ledger_row_digest(
                canonical.encode(),
                row[6].encode(),
                digest_buf,
                len(digest_buf),
            )
            assert rc == 0
            digests.append(digest_buf.value)

        arr = (ctypes.c_char_p * len(digests))()
        for i, digest in enumerate(digests):
            arr[i] = digest

        root_buf = ctypes.create_string_buffer(128)
        rc = lib.ledger_compute_chain_root(arr, len(digests), root_buf, len(root_buf))
        assert rc == 0
        root = root_buf.value.decode()
        assert root == compute_chain_root()
        assert root == CHAIN_ROOT
