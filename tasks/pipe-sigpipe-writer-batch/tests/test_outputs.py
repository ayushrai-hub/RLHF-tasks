from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPORT_PATH = Path("/app/output/run_records.json")
TRACE_PATH = Path("/app/output/ledger_trace.jsonl")
JOURNAL_PATH = Path("/app/output/span_journal.jsonl")
MANIFEST_PATH = Path("/app/output/run_manifest.jsonl")
AUDIT_PATH = Path("/app/output/run_audit.jsonl")
LEDGER_STATE_PATH = Path("/app/output/run_ledger.state")
FIXTURES_DIR = Path("/app/data/fixtures")
VERIFY_BIN = "/app/bin/verify-transfer-runs"


def _bundled_labels() -> tuple[str, ...]:
    return tuple(sorted(p.stem for p in FIXTURES_DIR.glob("pack_k*.json")))


def _openssl_digest(payload: str) -> str:
    proc = subprocess.run(
        ["openssl", "dgst", "-sha256"],
        input=payload.encode(),
        capture_output=True,
        check=True,
    )
    line = proc.stdout.decode().strip()
    return line.rsplit(maxsplit=1)[-1].replace(":", "")[:32]


def _mix_fingerprint(writer_epoch: str, reader_epoch: str, byte_span: dict[str, Any]) -> str:
    start = int(byte_span["start_offset"])
    end = int(byte_span["end_offset"])
    observed = int(byte_span["observed_bytes"])
    return _openssl_digest(f"{writer_epoch}|{reader_epoch}|{start}|{end}|{observed}")


def _journal_link(
    prev_link: str, seq: int, label: str, phase: str, observed: int, pending: int
) -> str:
    return _openssl_digest(f"{prev_link}|{seq}|{label}|{phase}|{observed}|{pending}")


def _checkpoint_seal(journal_tail: str, label: str, observed: int) -> str:
    return _openssl_digest(f"{journal_tail}|{label}|{observed}")


def _manifest_seal(journal_tail: str, trace_lines: int, wave_slices: int, observed: int) -> str:
    return _openssl_digest(f"{journal_tail}|{trace_lines}|{wave_slices}|{observed}")


def _audit_seal(journal_tail: str, manifest_seal: str, checkpoint_seal: str) -> str:
    return _openssl_digest(f"{journal_tail}|{manifest_seal}|{checkpoint_seal}")


def _run_ledger_seal(prev_tail: str, last_audit: str, run_count: int) -> str:
    return _openssl_digest(f"{prev_tail}|{last_audit}|{run_count}")


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _replay_expected(spec: dict[str, Any]) -> tuple[str, str, dict[str, int]]:
    writer = ""
    reader = ""
    observed = 0
    start = 0
    for event in spec.get("events", []):
        kind = event.get("kind")
        if kind == "seed":
            writer = str(event.get("writer_epoch", "")).lower()
            reader = str(event.get("reader_epoch", writer)).lower()
        elif kind == "wave":
            observed += int(event.get("bytes", 0))
        elif kind == "recycle":
            reader = str(event.get("reader_epoch", reader)).lower()
            writer = reader
    span = {
        "start_offset": start,
        "end_offset": start + observed,
        "observed_bytes": observed,
    }
    return writer, reader, span


def _rebuild_driver() -> None:
    subprocess.run(
        [
            "go",
            "build",
            "-o",
            "/app/bin/verify-transfer-runs",
            "/app/environment/cmd/verify-transfer-runs",
        ],
        cwd="/app/environment",
        check=True,
        capture_output=True,
        text=True,
    )


def _run_verify() -> None:
    _rebuild_driver()
    for path in (REPORT_PATH, TRACE_PATH, JOURNAL_PATH, MANIFEST_PATH, AUDIT_PATH):
        if path.exists():
            path.unlink()
    subprocess.run(
        [
            VERIFY_BIN,
            "--fixtures-dir",
            str(FIXTURES_DIR),
            "--out",
            str(REPORT_PATH),
            "--trace-out",
            str(TRACE_PATH),
            "--journal-out",
            str(JOURNAL_PATH),
            "--manifest-out",
            str(MANIFEST_PATH),
            "--audit-out",
            str(AUDIT_PATH),
            "--ledger-state",
            str(LEDGER_STATE_PATH),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _load_report() -> dict[str, Any]:
    _run_verify()
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _load_trace() -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    if not TRACE_PATH.exists():
        return lines
    for raw in TRACE_PATH.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            lines.append(json.loads(raw))
    return lines


def _load_journal() -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    if not JOURNAL_PATH.exists():
        return lines
    for raw in JOURNAL_PATH.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            lines.append(json.loads(raw))
    return lines


def _load_manifest() -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    if not MANIFEST_PATH.exists():
        return lines
    for raw in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            lines.append(json.loads(raw))
    return lines


def _load_audit() -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    if not AUDIT_PATH.exists():
        return lines
    for raw in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            lines.append(json.loads(raw))
    return lines


def _rows_by_label(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["fixture_label"]: row for row in report.get("runs", [])}


def _assert_row_matches_replay(row: dict[str, Any], journal: list[dict[str, Any]]) -> None:
    spec = _load_fixture(row["fixture_label"])
    exp_writer, exp_reader, span = _replay_expected(spec)
    assert row["writer_epoch"] == exp_writer
    assert row["reader_epoch"] == exp_reader
    assert row["byte_span"]["observed_bytes"] == span["observed_bytes"]
    assert row["byte_span"]["start_offset"] == span["start_offset"]
    assert row["byte_span"]["end_offset"] == span["end_offset"]
    expected_fp = _mix_fingerprint(row["writer_epoch"], row["reader_epoch"], row["byte_span"])
    assert row["fingerprint"] == expected_fp
    label = row["fixture_label"]
    jlines = [line for line in journal if line["fixture_label"] == label]
    assert jlines
    tail = jlines[-1]["link"]
    assert row.get("checkpoint_seal") == _checkpoint_seal(tail, label, span["observed_bytes"])


def _assert_journal_chain(lines: list[dict[str, Any]]) -> None:
    prev = "genesis"
    for line in lines:
        expected = _journal_link(
            prev,
            int(line["seq"]),
            line["fixture_label"],
            line["phase"],
            int(line["observed"]),
            int(line["pending"]),
        )
        assert line["link"] == expected
        prev = line["link"]


def _label_large_single_wrap() -> str:
    for label in _bundled_labels():
        spec = _load_fixture(label)
        if spec["sink_mode"] != "wrap":
            continue
        waves = [e for e in spec["events"] if e.get("kind") == "wave"]
        if not waves or waves[1:]:
            continue
        if int(waves[0]["bytes"]) > int(spec["pipe_cap"]):
            return label
    raise AssertionError("no single-wave wrap pack larger than pipe_cap")


def _label_with_multiple_recycles() -> str:
    for label in _bundled_labels():
        recycles = [e for e in _load_fixture(label)["events"] if e.get("kind") == "recycle"]
        if recycles and recycles[1:]:
            return label
    raise AssertionError("no pack with multiple recycle events")


def _label_post_recycle_large_waves() -> str:
    for label in _bundled_labels():
        spec = _load_fixture(label)
        if spec["sink_mode"] != "wrap":
            continue
        events = spec["events"]
        recycles = [i for i, e in enumerate(events) if e.get("kind") == "recycle"]
        if not recycles:
            continue
        after = events[recycles[-1] + 1 :]
        waves = [e for e in after if e.get("kind") == "wave"]
        if waves and int(waves[0]["bytes"]) > int(spec["pipe_cap"]):
            return label
    raise AssertionError("no post-recycle large-wave pack")


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    return _load_report()


@pytest.fixture(scope="module")
def trace() -> list[dict[str, Any]]:
    return _load_trace()


@pytest.fixture(scope="module")
def journal() -> list[dict[str, Any]]:
    return _load_journal()


@pytest.fixture(scope="module")
def manifest() -> list[dict[str, Any]]:
    return _load_manifest()


@pytest.fixture(scope="module")
def audit() -> list[dict[str, Any]]:
    return _load_audit()


def test_delayed_sidecar_reconcile(
    audit: list[dict[str, Any]], manifest: list[dict[str, Any]], report: dict[str, Any], journal: list[dict[str, Any]]
) -> None:
    """Post-run delayed pass reconciles report seals, manifest tails, and journal link chains per fixture."""
    assert audit
    rows = _rows_by_label(report)
    assert {line["fixture_label"] for line in audit} == set(_bundled_labels())
    manifest_by = {line["fixture_label"]: line for line in manifest}
    for aline in audit:
        label = aline["fixture_label"]
        row = rows[label]
        mline = manifest_by[label]
        jlines = [line for line in journal if line["fixture_label"] == label]
        assert jlines
        tail = jlines[-1]["link"]
        assert aline["journal_tail"] == tail
        assert mline["journal_tail"] == tail
        assert aline["manifest_seal"] == mline["manifest_seal"]
        assert aline["checkpoint_seal"] == row["checkpoint_seal"]
        assert aline["audit_seal"] == _audit_seal(tail, mline["manifest_seal"], row["checkpoint_seal"])
        _, _, span = _replay_expected(_load_fixture(label))
        assert row["byte_span"]["observed_bytes"] == span["observed_bytes"]


def test_post_recycle_wave_byte_totals(
    report: dict[str, Any], trace: list[dict[str, Any]], audit: list[dict[str, Any]]
) -> None:
    """Post-recycle large wave emits multiple wave_slice checkpoints and full byte totals after earlier packs."""
    label = _label_post_recycle_large_waves()
    spec = _load_fixture(label)
    want = sum(int(e["bytes"]) for e in spec["events"] if e.get("kind") == "wave")
    got = _rows_by_label(report)[label]["byte_span"]["observed_bytes"]
    assert got == want
    events = spec["events"]
    last_recycle = max(i for i, e in enumerate(events) if e.get("kind") == "recycle")
    second_wave = next(e for e in events[last_recycle + 1 :] if e.get("kind") == "wave")
    assert int(second_wave["bytes"]) > int(spec["pipe_cap"])
    slices = [line for line in trace if line["fixture_label"] == label and line["phase"] == "wave_slice"]
    assert len(slices) > 1
    aline = next(line for line in audit if line["fixture_label"] == label)
    assert aline["checkpoint_seal"] == _rows_by_label(report)[label]["checkpoint_seal"]


def test_wrap_large_wave_trace_totals(report: dict[str, Any], trace: list[dict[str, Any]]) -> None:
    """Metamorphic property: wave_slice observed+pending totals stay invariant until each wave completes."""
    label = _label_large_single_wrap()
    spec = _load_fixture(label)
    wave_total = sum(int(e["bytes"]) for e in spec["events"] if e.get("kind") == "wave")
    ends = [line for line in trace if line["fixture_label"] == label and line["phase"] == "wave_end"]
    assert ends
    last = ends[-1]
    assert last["pending"] == 0
    assert last["observed"] == wave_total
    assert _rows_by_label(report)[label]["byte_span"]["observed_bytes"] == wave_total
    slices = [line for line in trace if line["fixture_label"] == label and line["phase"] == "wave_slice"]
    assert slices
    totals = [int(line["observed"]) + int(line["pending"]) for line in slices]
    for prev, cur in zip(totals, totals[1:]):
        assert cur >= prev
    assert totals[-1] == wave_total


def test_multi_recycle_checkpoint_totals(
    trace: list[dict[str, Any]], journal: list[dict[str, Any]]
) -> None:
    """Dual-recycle pack flushes pending bytes before each recycle_before checkpoint in trace and journal."""
    label = _label_with_multiple_recycles()
    for artifact in (trace, journal):
        before = [line for line in artifact if line["fixture_label"] == label and line["phase"] == "recycle_before"]
        after = [line for line in artifact if line["fixture_label"] == label and line["phase"] == "recycle_after"]
        assert before and after
        for bline in before:
            assert bline["pending"] == 0
        for bline, aline in zip(before, after, strict=True):
            assert aline["observed"] == bline["observed"]
            assert aline["pending"] == 0


def test_journal_sequence_no_gaps(journal: list[dict[str, Any]]) -> None:
    """Journal sequence numbers increase monotonically across the full multi-fixture run."""
    assert journal
    seqs = [int(line["seq"]) for line in journal]
    assert seqs == list(range(1, len(seqs) + 1))
    for prev, cur in zip(seqs, seqs[1:]):
        assert cur > prev


def test_journal_link_hash_chain(journal: list[dict[str, Any]]) -> None:
    """Span journal link field chains sha256 checkpoints across the full fixture run order."""
    assert journal
    _assert_journal_chain(journal)
    labels = {line["fixture_label"] for line in journal}
    assert set(_bundled_labels()).issubset(labels)


def test_repeat_run_produces_identical_links() -> None:
    """Idempotency: two verify reruns produce identical journal link and audit seal sequences."""
    links: list[list[str]] = []
    audits: list[list[str]] = []
    for _ in range(2):
        _run_verify()
        lines = _load_journal()
        _assert_journal_chain(lines)
        links.append([line["link"] for line in lines])
        audits.append([line["audit_seal"] for line in _load_audit()])
    assert links[0] == links[1]
    assert audits[0] == audits[1]


def test_verify_overwrites_hand_written_outputs() -> None:
    """Hand-written report, trace, journal, manifest, and audit files are overwritten on verify."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text('{"runs":[]}\n', encoding="utf-8")
    TRACE_PATH.write_text('{"fixture_label":"tampered"}\n', encoding="utf-8")
    JOURNAL_PATH.write_text('{"seq":0,"link":"tampered"}\n', encoding="utf-8")
    MANIFEST_PATH.write_text('{"fixture_label":"tampered"}\n', encoding="utf-8")
    AUDIT_PATH.write_text('{"fixture_label":"tampered"}\n', encoding="utf-8")
    LEDGER_STATE_PATH.write_text(
        '{"run_count":0,"prev_audit_tail":"tampered","chain_seal":"tampered"}\n', encoding="utf-8"
    )
    _run_verify()
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert len(report["runs"]) == len(_bundled_labels())
    trace = _load_trace()
    journal = _load_journal()
    manifest = _load_manifest()
    audit = _load_audit()
    assert trace and trace[0]["fixture_label"] in _bundled_labels()
    assert journal and journal[0]["fixture_label"] in _bundled_labels()
    assert manifest and manifest[0]["fixture_label"] in _bundled_labels()
    assert audit and audit[0]["fixture_label"] in _bundled_labels()
    _assert_journal_chain(journal)
    ledger = json.loads(LEDGER_STATE_PATH.read_text(encoding="utf-8"))
    assert ledger["run_count"] == 1
    assert ledger["chain_seal"] != "tampered"


def test_cross_run_chain_advance() -> None:
    """Successive verify runs advance run_ledger.state by chaining prior and current final sidecar seals."""
    if LEDGER_STATE_PATH.exists():
        LEDGER_STATE_PATH.unlink()
    _run_verify()
    audit1 = _load_audit()
    ledger1 = json.loads(LEDGER_STATE_PATH.read_text(encoding="utf-8"))
    tail1 = audit1[-1]["audit_seal"]
    assert ledger1["run_count"] == 1
    assert ledger1["prev_audit_tail"] == tail1
    assert ledger1["chain_seal"] == _run_ledger_seal("genesis", tail1, 1)
    _run_verify()
    audit2 = _load_audit()
    ledger2 = json.loads(LEDGER_STATE_PATH.read_text(encoding="utf-8"))
    tail2 = audit2[-1]["audit_seal"]
    assert ledger2["run_count"] == 2
    assert ledger2["prev_audit_tail"] == tail2
    assert ledger2["chain_seal"] == _run_ledger_seal(tail1, tail2, 2)


def test_preload_offset_epoch_gate(report: dict[str, Any]) -> None:
    """Partial-state resume.offset with mismatched reader_epoch must not inflate pack_k3 totals."""
    label = "pack_k3"
    spec = _load_fixture(label)
    want = sum(int(e["bytes"]) for e in spec["events"] if e.get("kind") == "wave")
    got = _rows_by_label(report)[label]["byte_span"]["observed_bytes"]
    assert got == want


def _load_chunk_divisor() -> int:
    merged: dict[str, int] = {}
    config_dir = Path("/app/environment/config")
    for name in ("base.toml", "overlay.toml"):
        text = (config_dir / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("chunk_divisor"):
                continue
            _, _, raw = line.partition("=")
            merged["chunk_divisor"] = int(raw.strip())
    return merged.get("chunk_divisor", 1)


def _wrap_chunk_size(pipe_cap: int) -> int:
    chunk = pipe_cap // _load_chunk_divisor()
    return max(chunk, 512)


def _expected_wrap_wave_slices(spec: dict[str, Any]) -> int:
    if spec.get("sink_mode") != "wrap":
        return 0
    chunk = _wrap_chunk_size(int(spec["pipe_cap"]))
    total = 0
    for event in spec.get("events", []):
        if event.get("kind") != "wave":
            continue
        wave_bytes = int(event["bytes"])
        total += (wave_bytes + chunk - 1) // chunk
    return total


def test_overlay_slice_policy_fineness(manifest: list[dict[str, Any]]) -> None:
    """Slice policy: manifest wave_slices equals chunk-planned segment count for wrap pack_k5."""
    label = "pack_k5"
    spec = _load_fixture(label)
    want = _expected_wrap_wave_slices(spec)
    base_only = sum(
        (int(event["bytes"]) + int(spec["pipe_cap"]) - 1) // int(spec["pipe_cap"])
        for event in spec["events"]
        if event.get("kind") == "wave"
    )
    line = next(row for row in manifest if row["fixture_label"] == label)
    assert line["wave_slices"] == want
    assert want > base_only


def test_runtime_pack_k_discovery() -> None:
    """A runtime-added pack_k* fixture appears in report, manifest, and audit with matching seals."""
    redirect_label = next(
        label for label in _bundled_labels() if _load_fixture(label)["sink_mode"] == "redirect"
    )
    ref = _load_fixture(redirect_label)
    wave_bytes = sum(int(e["bytes"]) for e in ref["events"] if e.get("kind") == "wave")
    probe = FIXTURES_DIR / "pack_k7.json"
    spec = {
        "sink_mode": "wrap",
        "pipe_cap": int(ref["pipe_cap"]),
        "events": [
            {"kind": "seed", "writer_epoch": "p7aa01", "reader_epoch": "p7aa01"},
            {"kind": "wave", "bytes": wave_bytes},
        ],
    }
    probe.write_text(json.dumps(spec) + "\n", encoding="utf-8")
    try:
        _run_verify()
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        audit = _load_audit()
        manifest = _load_manifest()
        journal = _load_journal()
        assert "pack_k7" in _rows_by_label(report)
        assert any(line["fixture_label"] == "pack_k7" for line in audit)
        assert any(line["fixture_label"] == "pack_k7" for line in manifest)
        _assert_row_matches_replay(_rows_by_label(report)["pack_k7"], journal)
        aline = next(line for line in audit if line["fixture_label"] == "pack_k7")
        mline = next(line for line in manifest if line["fixture_label"] == "pack_k7")
        row = _rows_by_label(report)["pack_k7"]
        jlines = [line for line in journal if line["fixture_label"] == "pack_k7"]
        tail = jlines[-1]["link"]
        assert aline["journal_tail"] == tail
        assert aline["audit_seal"] == _audit_seal(tail, mline["manifest_seal"], row["checkpoint_seal"])
    finally:
        if probe.exists():
            probe.unlink()
