"""Verifier harness for arm64 tag reconciliation batch."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
OUT = APP / "output" / "tag_reconcile.json"
CHAIN = APP / "work" / "tag_chain.tsv"
PERSIST = APP / "work" / "tag_persist.bin"
MAIN = APP / "environment" / "fixtures" / "main_a64.elf"
DEP_TAGGED = APP / "environment" / "fixtures" / "dep_tagged.so"
DEP_UNTAGGED = APP / "environment" / "fixtures" / "dep_untagged.so"
INTERP = "/lib/ld-linux-aarch64.so.1"
INTERP_TABLE = APP / "environment" / "fixtures" / "interp_table.toml"
FW_B_LOG = APP / "environment" / "fixtures" / "buf_samples" / "fw_b.log"
ROUTES = APP / "environment" / "cfg" / "profile_routes.toml"
BUILD_A = APP / "environment" / "fixtures" / "spec_t2" / "build_a.toml"
BUILD_B = APP / "environment" / "fixtures" / "spec_t2" / "build_b.toml"

FIXTURE_PAYLOADS = {
    MAIN: bytes([0x04, 0x01, 0x00]),
    DEP_TAGGED: bytes([0x04, 0x01, 0x00]),
    DEP_UNTAGGED: bytes([0x00, 0x00, 0x00]),
}


def _fnv1a64(data: bytes) -> int:
    h = 14695981039346656037
    for b in data:
        h ^= b
        h = (h * 1099511628211) % (1 << 64)
    return h


def _hex16(v: int) -> str:
    return f"{v & 0xFFFFFFFFFFFF:016x}"


def _note_digest(path: Path) -> str:
    payload = FIXTURE_PAYLOADS[path]
    return _hex16(_fnv1a64(payload))


def _lineage_col(flags: int) -> str:
    h = _fnv1a64(INTERP.encode())
    prefix = _hex16(h)
    buf = prefix.encode() + flags.to_bytes(4, "little")
    return _hex16(_fnv1a64(buf))


def _chain_stamp(path: Path) -> str:
    return _hex16(_fnv1a64(path.read_bytes()))


def _u32_le(buf: bytes, off: int) -> int:
    return int.from_bytes(buf[off : off + 4], "little")


def _u64_le(buf: bytes, off: int) -> int:
    return int.from_bytes(buf[off : off + 8], "little")


def _elf_note_payload_offset(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    phoff = _u64_le(data, 32)
    ph = data[phoff : phoff + 56]
    p_type = _u32_le(ph, 0)
    p_offset = _u64_le(ph, 8)
    p_filesz = _u64_le(ph, 32)
    if p_type != 4 or p_filesz < 16:
        raise AssertionError(f"unexpected PT_NOTE layout in {path}")
    note = data[p_offset : p_offset + p_filesz]
    namesz = _u32_le(note, 0)
    descsz = _u32_le(note, 4)
    name_pad = namesz + ((4 - (namesz % 4)) % 4)
    payload_off = p_offset + 12 + name_pad
    return payload_off, descsz


def _patch_elf_note_payload(path: Path, payload: bytes) -> bytes:
    payload_off, descsz = _elf_note_payload_offset(path)
    if len(payload) != descsz:
        raise AssertionError(f"payload length {len(payload)} != note descsz {descsz}")
    original = path.read_bytes()
    patched = bytearray(original)
    patched[payload_off : payload_off + descsz] = payload
    path.write_bytes(patched)
    FIXTURE_PAYLOADS[path] = payload
    return original


def _run_batch() -> dict:
    if OUT.exists():
        OUT.unlink()
    proc = subprocess.run(["/app/tooling/run_h02.sh"], capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    assert OUT.is_file(), "harness must recreate tag_reconcile.json"
    return json.loads(OUT.read_text(encoding="utf-8"))


def _profile_obs(profile: str) -> int:
    log = APP / "environment" / "fixtures" / "buf_samples" / f"{profile}.log"
    for line in log.read_text(encoding="utf-8").splitlines():
        if line.startswith("obs="):
            return int(line.split("=", 1)[1].split()[0])
    raise AssertionError(f"missing obs in {log}")


def _row(doc: dict, profile: str) -> dict:
    return next(r for r in doc["rows"] if r["profile"] == profile)


def _expected_matrix_counts() -> tuple[int, int]:
    main_d = _note_digest(MAIN)
    mism = sum(1 for p in (DEP_TAGGED, DEP_UNTAGGED) if _note_digest(p) != main_d)
    return mism, mism


def _route_dep_fixture(profile: str) -> Path:
    text = ROUTES.read_text(encoding="utf-8")
    active = False
    for line in text.splitlines():
        if line.strip() == f"[{profile}]":
            active = True
            continue
        if active and line.startswith("[") and line.strip() != f"[{profile}]":
            break
        if active and "dep_fixture" in line:
            name = line.split("=", 1)[1].strip().strip('"')
            return APP / "environment" / "fixtures" / name
    raise AssertionError(f"missing dep_fixture route for {profile}")


def _parse_chain(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        profile, viol, asym, fault, lineage = line.split("\t")
        rows.append(
            {
                "profile": profile,
                "scan_violations": int(viol),
                "asym_delta": int(asym),
                "fault_obs": int(fault),
                "lineage_col": lineage,
            }
        )
    return rows


@pytest.fixture(scope="session", autouse=True)
def _ensure_batch_built() -> None:
    subprocess.run(["make", "-C", "/app/environment", "all"], check=True)


@pytest.fixture(scope="session")
def trace_doc() -> dict:
    return _run_batch()


def test_z0_regen_batch(trace_doc: dict) -> None:
    """Build succeeds and deleting output then running the batch recreates schema-valid rows."""
    assert set(trace_doc) == {"rows", "summary"}
    summary = trace_doc["summary"]
    assert summary["batch_stamp"] == "tag-v2"
    assert summary["row_count"] == len(trace_doc["rows"])
    assert "chain_stamp" in summary
    assert len(summary["chain_stamp"]) == 16
    required = {
        "profile",
        "main_digest_hex",
        "dep_digest_hex",
        "lineage_col",
        "so_delta",
        "scan_violations",
        "fault_obs",
    }
    profiles = []
    for row in trace_doc["rows"]:
        assert required <= set(row)
        profiles.append(row["profile"])
    assert set(profiles) == {"fw_a", "fw_b"}
    assert PERSIST.is_file(), "batch must seal graph walk totals into tag_persist.bin"


def test_z1_profile_dep_route(trace_doc: dict) -> None:
    """Each profile row resolves dep_digest_hex from profile_routes.toml, not one global fixture."""
    for profile in ("fw_a", "fw_b"):
        want = _note_digest(_route_dep_fixture(profile))
        assert _row(trace_doc, profile)["dep_digest_hex"] == want
    assert _row(trace_doc, "fw_a")["dep_digest_hex"] != _row(trace_doc, "fw_b")["dep_digest_hex"]


def test_z2_lineage_converge(trace_doc: dict) -> None:
    """Lineage columns match the interp table once merge flags honor PT_INTERP hash rows."""
    want = _lineage_col(1)
    for profile in ("fw_a", "fw_b"):
        assert _row(trace_doc, profile)["lineage_col"] == want


def test_z3_delta_converge(trace_doc: dict) -> None:
    """Transitive shared-object delta counters reflect dependent visits, not main-only checks."""
    want_delta, want_viol = _expected_matrix_counts()
    row = _row(trace_doc, "fw_a")
    assert row["so_delta"] == want_delta
    assert row["scan_violations"] == want_viol


def test_z4_persist_graph_seal(trace_doc: dict) -> None:
    """fw_a scan_violations must follow the graph walk seal, not the legacy main-only persist probe."""
    _, want_viol = _expected_matrix_counts()
    fw_a = _row(trace_doc, "fw_a")
    fw_b = _row(trace_doc, "fw_b")
    assert fw_b["scan_violations"] == want_viol
    assert fw_a["scan_violations"] == want_viol
    assert fw_a["scan_violations"] != 0 or want_viol == 0


def test_z5_dep_link_tag_symmetry(trace_doc: dict) -> None:
    """Symmetric dep link_tag values let both profiles share fw_a adjusted fault observations."""
    fw_a = _row(trace_doc, "fw_a")
    fw_b = _row(trace_doc, "fw_b")
    _, want_viol = _expected_matrix_counts()
    want_fault = max(0, _profile_obs("fw_a") - want_viol)
    assert fw_a["fault_obs"] == want_fault
    assert fw_b["fault_obs"] == want_fault


def test_z6_interp_table_mutation() -> None:
    """Lineage tracks live interp_table.toml cap rows instead of hardcoded note checks."""
    original = INTERP_TABLE.read_text(encoding="utf-8")
    try:
        INTERP_TABLE.write_text(original.replace("cap_byte = 4", "cap_byte = 0"), encoding="utf-8")
        doc = _run_batch()
        want = _lineage_col(0)
        for profile in ("fw_a", "fw_b"):
            assert _row(doc, profile)["lineage_col"] == want
    finally:
        INTERP_TABLE.write_text(original, encoding="utf-8")
        _run_batch()


def test_z7_dependent_walk_mutation() -> None:
    """Violation counts walk every dependent fixture, not just the first shared object."""
    original = DEP_TAGGED.read_bytes()
    try:
        _patch_elf_note_payload(DEP_TAGGED, bytes([0x00, 0x00, 0x00]))
        doc = _run_batch()
        row = _row(doc, "fw_a")
        assert row["scan_violations"] == 2
        assert row["so_delta"] == 2
    finally:
        DEP_TAGGED.write_bytes(original)
        FIXTURE_PAYLOADS[DEP_TAGGED] = bytes([0x04, 0x01, 0x00])
        _run_batch()


def test_z8_buf_sample_adjustment_live() -> None:
    """fw_b fault observations follow shared adjustment logic instead of raw buffer samples."""
    original = FW_B_LOG.read_text(encoding="utf-8")
    try:
        FW_B_LOG.write_text("obs=9 line=fw_b\n", encoding="utf-8")
        doc = _run_batch()
        fw_a = _row(doc, "fw_a")
        fw_b = _row(doc, "fw_b")
        assert fw_a["fault_obs"] == fw_b["fault_obs"]
        assert fw_b["fault_obs"] != 9
    finally:
        FW_B_LOG.write_text(original, encoding="utf-8")
        _run_batch()


def test_z9_chain_journal_seal(trace_doc: dict) -> None:
    """Journal lines must record finalized profile state before chain_stamp is derived."""
    assert CHAIN.is_file(), "batch must persist tag_chain.tsv"
    chain_rows = _parse_chain(CHAIN)
    assert len(chain_rows) == 2
    _, want_viol = _expected_matrix_counts()
    want_lineage = _lineage_col(1)
    by_profile = {row["profile"]: row for row in chain_rows}
    for profile in ("fw_a", "fw_b"):
        out_row = _row(trace_doc, profile)
        chain_row = by_profile[profile]
        assert chain_row["scan_violations"] == want_viol
        assert chain_row["fault_obs"] == out_row["fault_obs"]
        assert chain_row["lineage_col"] == want_lineage
        assert out_row["lineage_col"] == want_lineage
    assert trace_doc["summary"]["chain_stamp"] == _chain_stamp(CHAIN)


def test_z10_idempotent_rerun(trace_doc: dict) -> None:
    """Re-running the batch without edits must leave row fields and chain_stamp unchanged."""
    second = _run_batch()
    assert second["summary"]["chain_stamp"] == trace_doc["summary"]["chain_stamp"]
    for profile in ("fw_a", "fw_b"):
        assert _row(second, profile) == _row(trace_doc, profile)


def test_z11_link_tag_asymmetry_probe() -> None:
    """Lowering build_b dep link_tag surfaces asymmetric fw_b fault observations once emit reads dep rows."""
    original_b = BUILD_B.read_text(encoding="utf-8")
    try:
        lines: list[str] = []
        in_dep = False
        for line in original_b.splitlines():
            if line.strip() == "[dep]":
                in_dep = True
            elif line.startswith("[") and in_dep:
                in_dep = False
            if in_dep and "link_tag" in line:
                lines.append("link_tag = 0")
            else:
                lines.append(line)
        BUILD_B.write_text("\n".join(lines) + "\n", encoding="utf-8")
        doc = _run_batch()
        fw_b = _row(doc, "fw_b")
        assert fw_b["fault_obs"] == _profile_obs("fw_b")
        assert fw_b["fault_obs"] != _row(doc, "fw_a")["fault_obs"]
    finally:
        BUILD_B.write_text(original_b, encoding="utf-8")
        _run_batch()
