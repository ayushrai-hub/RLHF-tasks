from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import struct
import subprocess
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest


APP = Path(os.environ.get("APP_DIR", "/app"))
FIXTURE = APP / "fixtures" / "omega"


@pytest.fixture(scope="session")
def binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("bin") / "breach-ledger"
    result = subprocess.run(
        ["/usr/local/go/bin/go", "build", "-o", str(out), "/app/cmd/breach-ledger"],
        cwd=APP,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return out


def copy_bundle(tmp_path: Path) -> Path:
    dest = tmp_path / "bundle"
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE, dest)
    return dest


def run_cli(binary: Path, bundle: Path, output: Path, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary), "--bundle", str(bundle), "--output", str(output)],
        cwd=APP,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_ok(binary: Path, bundle: Path, output: Path) -> tuple[dict, list[dict[str, str]]]:
    result = run_cli(binary, bundle, output)
    assert result.returncode == 0, result.stderr
    report = read_json(output / "incident_report.json")
    with (output / "attack_timeline.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return report, rows


def assert_rejected(binary: Path, bundle: Path, output: Path, code: str) -> None:
    result = run_cli(binary, bundle, output)
    assert result.returncode != 0
    report = read_json(output / "incident_report.json")
    assert report["status"] == "rejected"
    assert report["error"]["code"] == code


def rewrite_sqlite(path: Path, rows: list[tuple[str, str, str, int, str]]) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE deleted_files (path TEXT NOT NULL, sha256 TEXT NOT NULL, deleted_at TEXT NOT NULL, size INTEGER NOT NULL, recovered_from TEXT NOT NULL)"
    )
    conn.executemany("INSERT INTO deleted_files VALUES (?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()


def add_duplicate_user(bundle: Path) -> None:
    path = bundle / "inventory" / "users.json"
    users = json.loads(path.read_text(encoding="utf-8"))
    users.append({"username": "backup", "uid": 9999, "role": "conflict", "aliases": []})
    path.write_text(json.dumps(users), encoding="utf-8")


def add_conflicting_host(bundle: Path) -> None:
    path = bundle / "inventory" / "hosts.json"
    hosts = json.loads(path.read_text(encoding="utf-8"))
    hosts.append({"host": "shard-9", "role": "conflict", "aliases": ["db"]})
    path.write_text(json.dumps(hosts), encoding="utf-8")


def duplicate_auth_seq(bundle: Path) -> None:
    path = bundle / "logs" / "auth.log"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("seq=1003", "seq=1002", 1), encoding="utf-8")


def malformed_audit(bundle: Path) -> None:
    (bundle / "audit" / "frames.bin").write_bytes(struct.pack(">I", 5000) + b"{bad")


def write_archive(bundle: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(bundle / "archives" / "staged.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def decoded_secret_lines(bundle: Path) -> tuple[list[str], str]:
    manifest = json.loads((bundle / "secrets" / "manifest.json").read_text(encoding="utf-8"))
    key = int(manifest["xor_key_hex"], 16)
    payload = b""
    for item in manifest["fragments"]:
        raw = base64.b64decode((bundle / item["path"]).read_text(encoding="utf-8").strip())
        decoded = bytes(byte ^ key for byte in raw)
        payload += gzip.decompress(decoded)
    digest = hashlib.sha256(payload).hexdigest()
    return sorted(line.decode("utf-8") for line in payload.splitlines() if line), digest


def kv_pairs(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in line.strip().split():
        if "=" in part:
            key, value = part.split("=", 1)
            out[key] = value.strip('"')
    return out


def auth_records(bundle: Path) -> list[dict[str, str]]:
    records = [kv_pairs(line) for line in (bundle / "logs" / "auth.log").read_text(encoding="utf-8").splitlines() if line.strip()]
    rotated = bundle / "logs" / "auth.log.1.gz"
    if rotated.exists():
        records.extend(kv_pairs(line) for line in gzip.decompress(rotated.read_bytes()).decode("utf-8").splitlines() if line.strip())
    return records


def accepted_password_record(bundle: Path) -> dict[str, str]:
    return min(
        (row for row in auth_records(bundle) if row.get("event") == "accepted" and row.get("method") == "password"),
        key=lambda row: int(row["seq"]),
    )


def web_vulnerability_record(bundle: Path) -> dict:
    records = [json.loads(line) for line in (bundle / "web" / "access.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    return min(
        (row for row in records if row.get("vulnerability") and int(row.get("status", 0)) < 400),
        key=lambda row: int(row["seq"]),
    )


def deleted_rows(bundle: Path) -> list[tuple[str, str, str, int, str]]:
    conn = sqlite3.connect(bundle / "deleted" / "deleted.sqlite")
    try:
        return list(conn.execute("SELECT path, sha256, deleted_at, size, recovered_from FROM deleted_files ORDER BY path"))
    finally:
        conn.close()


def archive_exfil(bundle: Path) -> dict:
    with zipfile.ZipFile(bundle / "archives" / "staged.zip") as zf:
        for name in sorted(zf.namelist()):
            try:
                item = json.loads(zf.read(name).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if {"destination_ip", "protocol", "bytes", "timestamp", "files"}.issubset(item):
                return item
    raise AssertionError("no exfil manifest found")


def archive_commands(bundle: Path) -> list[str]:
    commands: list[str] = []
    with zipfile.ZipFile(bundle / "archives" / "staged.zip") as zf:
        for name in sorted(zf.namelist()):
            data = zf.read(name)
            if name.endswith(".gz"):
                data = gzip.decompress(data)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" ", 3)
                if len(parts) == 4:
                    commands.append(parts[3])
                else:
                    commands.append(line)
    return commands


def expected_stolen_files(bundle: Path) -> list[str]:
    files = {row[0] for row in deleted_rows(bundle)}
    files.update(archive_exfil(bundle).get("files", []))
    return sorted(files)


def expected_iocs(bundle: Path) -> set[str]:
    out: set[str] = set()
    auth = accepted_password_record(bundle)
    out.add("ip:" + auth["src"])
    web = web_vulnerability_record(bundle)
    out.add("cve:" + web["vulnerability"])
    out.add("url:" + web["path"])
    exfil = archive_exfil(bundle)
    out.add("ip:" + exfil["destination_ip"])
    for line in (bundle / "network" / "dns.log").read_text(encoding="utf-8").splitlines():
        row = kv_pairs(line)
        query = row.get("query")
        if query and row.get("user") != "svc-metrics":
            out.add("domain:" + query)
    _, digest = decoded_secret_lines(bundle)
    out.add("secret-sha256:" + digest)
    return out


def first_history_command(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if "cmd=" in line:
            return line.split("cmd=", 1)[1]
        if line.strip() and not line.lstrip().startswith("#"):
            return line
    raise AssertionError("history command not found")


def before_timestamp(ts: str) -> str:
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (parsed - timedelta(hours=1)).isoformat().replace("+00:00", "Z")


def audit_frames(bundle: Path) -> list[dict]:
    data = (bundle / "audit" / "frames.bin").read_bytes()
    offset = 0
    frames: list[dict] = []
    while offset + 4 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4
        payload = data[offset : offset + length]
        offset += length
        frames.append(json.loads(payload.decode("utf-8")))
    return frames


def expected_tampered_events(bundle: Path) -> list[dict]:
    out: list[dict] = []
    for frame in audit_frames(bundle):
        claimed = frame.get("claimed_ts", "")
        true_ts = frame.get("ts", "")
        if claimed and claimed != true_ts:
            out.append(
                {
                    "seq": frame["seq"],
                    "host": frame["host"].lower(),
                    "user": frame["user"].lower(),
                    "claimed_ts": claimed,
                    "true_ts": true_ts,
                    "detail": frame["detail"],
                }
            )
    return sorted(out, key=lambda item: item["seq"])


def expected_persistence(bundle: Path) -> list[str]:
    out: list[str] = []
    for path in sorted((bundle / "persistence" / "cron.d").glob("*")):
        meta = kv_pairs(path.read_text(encoding="utf-8").splitlines()[0].lstrip("#"))
        out.append(f"cron:{meta['host']}:/etc/cron.d/{path.name}")
    for path in sorted((bundle / "persistence" / "systemd").glob("*")):
        meta = kv_pairs(path.read_text(encoding="utf-8").splitlines()[0].lstrip("#"))
        out.append(f"systemd:{meta['host']}:{path.name}")
    for path in sorted((bundle / "persistence" / "shell").glob("*")):
        meta = kv_pairs(path.read_text(encoding="utf-8").splitlines()[0].lstrip("#"))
        out.append(f"shell:{meta['user']}:{meta['path']}")
    return sorted(out)


def test_full_report_accepts_real_bundle(binary: Path, tmp_path: Path) -> None:
    """The unmodified omega bundle produces the complete accepted incident report."""
    bundle = copy_bundle(tmp_path)
    before_manifest = (bundle / "configs" / "manifest.json").read_bytes()
    report, rows = run_ok(binary, bundle, tmp_path / "out")
    auth = accepted_password_record(bundle)
    web = web_vulnerability_record(bundle)

    assert report["schema_version"] == 2
    assert report["status"] == "accepted"
    assert report["classification"] == "multi_hop_intrusion"
    assert [item["attacker_id"] for item in report["initial_access"]] == ["A", "B"]
    assert report["initial_access"][0] == {
        "attacker_id": "A",
        "host": auth["host"],
        "vector": "ssh_password_spray",
        "vulnerability": "weak_password_reuse",
        "account": auth["user"],
        "source_ip": auth["src"],
        "timestamp": auth["ts"],
    }
    assert report["initial_access"][1]["vulnerability"] == web["vulnerability"]
    assert report["compromised_hosts"] == ["db-3", "edge-1", "web-2"]
    assert report["compromised_accounts"] == ["backup", "root", "www-data"]
    assert len(rows) >= 24
    assert (bundle / "configs" / "manifest.json").read_bytes() == before_manifest


def test_parse_summary_counts_all_evidence_families(binary: Path, tmp_path: Path) -> None:
    """Every supported evidence family contributes to parse_summary counts."""
    report, _ = run_ok(binary, copy_bundle(tmp_path), tmp_path / "out")
    summary = report["parse_summary"]
    assert summary["auth_entries"] == 8
    assert summary["web_entries"] == 3
    assert summary["history_entries"] == 9
    assert summary["persistence_entries"] == 3
    assert summary["dns_entries"] == 3
    assert summary["egress_entries"] == 3
    assert summary["audit_frames"] == 4
    assert summary["deleted_files"] == 3
    assert summary["git_events"] == 2
    assert summary["secret_fragments"] == 3
    assert summary["archive_entries"] == 2
    assert summary["config_files"] == 2
    assert summary["process_snapshots"] == 4
    assert summary["container_entries"] == 2


def test_timeline_csv_is_sorted_and_clean(binary: Path, tmp_path: Path) -> None:
    """The CSV timeline uses the strict header, stable ordering, and clean details."""
    _, rows = run_ok(binary, copy_bundle(tmp_path), tmp_path / "out")
    assert rows[0].keys() == {"seq", "ts", "host", "user", "source", "action", "detail", "attacker_id"}
    sort_keys = [(row["ts"], int(row["seq"]), row["host"], row["action"], row["detail"]) for row in rows]
    assert sort_keys == sorted(sort_keys)
    assert all("\x00" not in row["detail"] for row in rows)
    assert {"auth", "web", "history", "audit", "archive", "process", "container"}.issubset({row["source"] for row in rows})


def test_repeated_runs_are_byte_identical(binary: Path, tmp_path: Path) -> None:
    """Repeated runs over identical evidence produce identical artifact bytes."""
    bundle = copy_bundle(tmp_path)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    assert run_cli(binary, bundle, out_a).returncode == 0
    assert run_cli(binary, bundle, out_b).returncode == 0
    for name in ("incident_report.json", "attack_timeline.csv", "iocs.txt", "remediation_plan.json"):
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes()


def test_equivalent_reordered_jsonl_inputs_are_stable(binary: Path, tmp_path: Path) -> None:
    """Equivalent JSONL record order changes do not alter deterministic outputs."""
    base = copy_bundle(tmp_path / "omega")
    variant = copy_bundle(tmp_path / "fixtures")
    for rel in ("web/access.jsonl", "proc/snapshots.jsonl", "git/events.jsonl", "containers/list.jsonl"):
        path = variant / rel
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    assert run_cli(binary, base, out_a).returncode == 0
    assert run_cli(binary, variant, out_b).returncode == 0
    assert (out_a / "incident_report.json").read_bytes() == (out_b / "incident_report.json").read_bytes()
    assert (out_a / "attack_timeline.csv").read_bytes() == (out_b / "attack_timeline.csv").read_bytes()


def test_rotated_gzip_auth_log_is_used(binary: Path, tmp_path: Path) -> None:
    """Rotated gzip auth logs are parsed together with the active auth log."""
    bundle = copy_bundle(tmp_path)
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    assert report["parse_summary"]["auth_entries"] == 8
    assert "ip:" + accepted_password_record(bundle)["src"] in report["iocs"]


def test_secret_fragments_decode_to_stolen_secrets(binary: Path, tmp_path: Path) -> None:
    """Encoded secret fragments decode, concatenate, and match the digest."""
    bundle = copy_bundle(tmp_path)
    expected_lines, digest = decoded_secret_lines(bundle)
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    assert report["stolen_secrets"] == expected_lines
    assert f"secret-sha256:{digest}" in report["iocs"]


def test_deleted_sqlite_catalog_contributes_files(binary: Path, tmp_path: Path) -> None:
    """The SQLite deleted-file catalog contributes stolen file paths."""
    bundle = copy_bundle(tmp_path)
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    assert report["stolen_files"] == expected_stolen_files(bundle)


def test_config_drift_and_remediation_are_reported(binary: Path, tmp_path: Path) -> None:
    """Config hash drift is reflected in report fields and remediation actions."""
    bundle = copy_bundle(tmp_path)
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    remediation = read_json(tmp_path / "out" / "remediation_plan.json")
    assert report["modified_configs"] == ["nginx.conf", "sshd_config"]
    assert remediation["golden_config_changed"] is False
    assert remediation["modified_config_count"] == 2
    assert {f"restore_config:{name}" for name in report["modified_configs"]}.issubset(remediation["actions"])
    assert {f"remove:{item}" for item in report["persistence"]}.issubset(remediation["actions"])


def test_tampered_events_from_audit_frames(binary: Path, tmp_path: Path) -> None:
    """Trusted audit frames with timestamp skew appear in tampered_events."""
    bundle = copy_bundle(tmp_path)
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    expected = expected_tampered_events(bundle)
    assert expected
    assert report["tampered_events"] == expected
    assert all(item["claimed_ts"] != item["true_ts"] for item in report["tampered_events"])


def test_persistence_entries_match_contract(binary: Path, tmp_path: Path) -> None:
    """Persistence markers use the cron, systemd, and shell formats from the contract."""
    bundle = copy_bundle(tmp_path)
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    assert report["persistence"] == expected_persistence(bundle)


def test_commands_include_hostile_sources(binary: Path, tmp_path: Path) -> None:
    """The commands array chronologically includes history, audit, and archive sources."""
    bundle = copy_bundle(tmp_path)
    report, rows = run_ok(binary, bundle, tmp_path / "out")
    cmds = report["commands"]
    assert len(cmds) >= 6
    archive_cmds = archive_commands(bundle)
    history_cmds = [
        first_history_command(path)
        for path in sorted((bundle / "histories").glob("*.bash_history"))
    ]
    assert any(cmd in cmds for cmd in history_cmds)
    assert any(cmd in cmds for cmd in archive_cmds)
    assert any(row["source"] == "audit" and row["detail"] in cmds for row in rows)


def test_false_leads_are_exonerated(binary: Path, tmp_path: Path) -> None:
    """Noisy service-account and internal-address evidence stays exonerated."""
    report, _ = run_ok(binary, copy_bundle(tmp_path), tmp_path / "out")
    assert report["false_leads"] == ["172.16.10.55", "svc-metrics"]
    assert "svc-metrics" not in report["compromised_accounts"]


def test_ioc_file_is_sorted_unique_and_matches_report(binary: Path, tmp_path: Path) -> None:
    """The IOC text artifact is sorted, unique, and equal to report iocs."""
    bundle = copy_bundle(tmp_path)
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    lines = (tmp_path / "out" / "iocs.txt").read_text(encoding="utf-8").splitlines()
    assert lines == sorted(set(lines))
    assert lines == report["iocs"]
    for expected in expected_iocs(bundle):
        assert expected in lines


def test_path_traversal_outranks_identity_conflict(binary: Path, tmp_path: Path) -> None:
    """Deleted metadata path traversal wins over lower-priority identity conflicts."""
    bundle = copy_bundle(tmp_path)
    rewrite_sqlite(bundle / "deleted" / "deleted.sqlite", [("../etc/passwd", "aa" * 32, "2026-06-10T02:00:00Z", 1, "journal")])
    add_duplicate_user(bundle)
    assert_rejected(binary, bundle, tmp_path / "out", "path_traversal")


def test_archive_escape_outranks_malformed_audit(binary: Path, tmp_path: Path) -> None:
    """Unsafe zip member names outrank malformed binary audit frames."""
    bundle = copy_bundle(tmp_path)
    write_archive(bundle, {"../escape": b"bad"})
    malformed_audit(bundle)
    assert_rejected(binary, bundle, tmp_path / "out", "archive_escape")


def test_malformed_binary_frame_outranks_identity_conflict(binary: Path, tmp_path: Path) -> None:
    """Malformed audit frames outrank identity conflicts in rejection priority."""
    bundle = copy_bundle(tmp_path)
    malformed_audit(bundle)
    add_duplicate_user(bundle)
    assert_rejected(binary, bundle, tmp_path / "out", "malformed_binary_frame")


def test_identity_conflict_outranks_ssh_sequence(binary: Path, tmp_path: Path) -> None:
    """Conflicting user identity records outrank duplicate SSH sequence numbers."""
    bundle = copy_bundle(tmp_path)
    add_duplicate_user(bundle)
    duplicate_auth_seq(bundle)
    assert_rejected(binary, bundle, tmp_path / "out", "identity_conflict")


def test_host_conflict_outranks_ssh_sequence(binary: Path, tmp_path: Path) -> None:
    """Conflicting host alias records outrank duplicate SSH sequence numbers."""
    bundle = copy_bundle(tmp_path)
    add_conflicting_host(bundle)
    duplicate_auth_seq(bundle)
    assert_rejected(binary, bundle, tmp_path / "out", "host_conflict")


def test_host_conflict_rejects(binary: Path, tmp_path: Path) -> None:
    """Conflicting host alias bindings reject with host_conflict."""
    bundle = copy_bundle(tmp_path)
    add_conflicting_host(bundle)
    assert_rejected(binary, bundle, tmp_path / "out", "host_conflict")


def test_ssh_sequence_violation_rejects(binary: Path, tmp_path: Path) -> None:
    """Duplicate SSH auth sequence numbers reject when higher priorities are absent."""
    bundle = copy_bundle(tmp_path)
    duplicate_auth_seq(bundle)
    assert_rejected(binary, bundle, tmp_path / "out", "ssh_sequence_violation")


def test_secret_fragment_digest_mismatch_rejects(binary: Path, tmp_path: Path) -> None:
    """A mutated encoded secret fragment rejects with the secret conflict code."""
    bundle = copy_bundle(tmp_path)
    (bundle / "secrets" / "fragments" / "part2.b64").write_text(base64.b64encode(b"wrong").decode(), encoding="utf-8")
    assert_rejected(binary, bundle, tmp_path / "out", "secret_fragment_conflict")


def test_deleted_metadata_conflict_rejects(binary: Path, tmp_path: Path) -> None:
    """Conflicting SQLite rows for the same deleted path reject precisely."""
    bundle = copy_bundle(tmp_path)
    path, _, deleted_at, _, recovered_from = deleted_rows(bundle)[0]
    rewrite_sqlite(
        bundle / "deleted" / "deleted.sqlite",
        [
            (path, "aa" * 32, deleted_at, 100, recovered_from),
            (path, "bb" * 32, deleted_at.replace("Z", "1Z"), 101, recovered_from),
        ],
    )
    assert_rejected(binary, bundle, tmp_path / "out", "deleted_meta_conflict")


def test_git_history_conflict_rejects(binary: Path, tmp_path: Path) -> None:
    """Duplicate Git commit ids with different payloads reject precisely."""
    bundle = copy_bundle(tmp_path)
    path = bundle / "git" / "events.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write('{"commit_id":"c0ffee01","ts":"2026-06-10T02:50:00Z","host":"edge-1","author":"backup","action":"delete","path":"/etc/passwd"}\n')
    assert_rejected(binary, bundle, tmp_path / "out", "git_history_conflict")


def test_process_conflict_rejects(binary: Path, tmp_path: Path) -> None:
    """Duplicate process keys with conflicting payloads reject precisely."""
    bundle = copy_bundle(tmp_path)
    path = bundle / "proc" / "snapshots.jsonl"
    first = path.read_text(encoding="utf-8").splitlines()[0]
    with path.open("a", encoding="utf-8") as f:
        f.write(first.replace("/tmp/.p --stage", "/bin/false") + "\n")
    assert_rejected(binary, bundle, tmp_path / "out", "process_conflict")


def test_timeline_conflict_rejects(binary: Path, tmp_path: Path) -> None:
    """Attacker actions that predate their initial access reject as timeline conflicts."""
    bundle = copy_bundle(tmp_path)
    path = bundle / "histories" / "backup.bash_history"
    old_ts = kv_pairs(path.read_text(encoding="utf-8").splitlines()[0])["ts"]
    text = path.read_text(encoding="utf-8").replace("ts=" + old_ts, "ts=" + before_timestamp(accepted_password_record(bundle)["ts"]), 1)
    path.write_text(text, encoding="utf-8")
    assert_rejected(binary, bundle, tmp_path / "out", "timeline_conflict")


def test_missing_required_evidence_rejects(binary: Path, tmp_path: Path) -> None:
    """Removing one intrusion path yields the missing evidence rejection."""
    bundle = copy_bundle(tmp_path)
    (bundle / "web" / "access.jsonl").unlink()
    assert_rejected(binary, bundle, tmp_path / "out", "missing_required_evidence")


def test_rejection_writes_only_rejection_report(binary: Path, tmp_path: Path) -> None:
    """Rejected bundles write the rejection report without accepted-run artifacts."""
    bundle = copy_bundle(tmp_path)
    malformed_audit(bundle)
    out = tmp_path / "out"
    assert_rejected(binary, bundle, out, "malformed_binary_frame")
    assert (out / "incident_report.json").exists()
    assert not (out / "attack_timeline.csv").exists()
    assert not (out / "iocs.txt").exists()


def test_null_bytes_inside_history_commands_are_removed(binary: Path, tmp_path: Path) -> None:
    """Null bytes embedded in shell history commands are stripped from outputs."""
    bundle = copy_bundle(tmp_path)
    path = bundle / "histories" / "root.bash_history"
    command = first_history_command(path)
    text = path.read_text(encoding="utf-8").replace(command, command.replace(" ", "\x00 ", 1), 1)
    path.write_text(text, encoding="utf-8")
    report, rows = run_ok(binary, bundle, tmp_path / "out")
    assert command in report["commands"]
    assert all("\x00" not in row["detail"] for row in rows)


def test_zero_width_username_in_history_is_canonicalized(binary: Path, tmp_path: Path) -> None:
    """Zero-width characters in usernames are removed during normalization."""
    bundle = copy_bundle(tmp_path)
    path = bundle / "histories" / "backup.bash_history"
    text = path.read_text(encoding="utf-8").replace("user=backup", "user=ba\u200bckup", 1)
    path.write_text(text, encoding="utf-8")
    report, rows = run_ok(binary, bundle, tmp_path / "out")
    assert "backup" in report["compromised_accounts"]
    assert any(row["user"] == "backup" for row in rows)


def test_crlf_auth_log_still_parses(binary: Path, tmp_path: Path) -> None:
    """CRLF line endings in auth logs do not break parsing or correlation."""
    bundle = copy_bundle(tmp_path)
    account = accepted_password_record(bundle)["user"]
    path = bundle / "logs" / "auth.log"
    path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    assert report["parse_summary"]["auth_entries"] == 8
    assert report["initial_access"][0]["account"] == account


def test_large_noise_logs_remain_fast_and_stable(binary: Path, tmp_path: Path) -> None:
    """Large benign auth-log noise stays efficient and does not change attribution."""
    bundle = copy_bundle(tmp_path)
    source_ip = accepted_password_record(bundle)["src"]
    with (bundle / "logs" / "auth.log").open("a", encoding="utf-8") as f:
        for i in range(3000):
            f.write(f"seq={20000+i} ts=2026-06-10T03:00:00Z host=edge-1 user=deploy src=10.10.0.5 event=accepted method=publickey\n")
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    assert report["initial_access"][0]["source_ip"] == source_ip
    assert report["parse_summary"]["auth_entries"] == 3008


def test_identical_duplicate_process_records_are_tolerated(binary: Path, tmp_path: Path) -> None:
    """Identical duplicate process records increment counts without conflict."""
    bundle = copy_bundle(tmp_path)
    path = bundle / "proc" / "snapshots.jsonl"
    first = path.read_text(encoding="utf-8").splitlines()[0]
    with path.open("a", encoding="utf-8") as f:
        f.write(first + "\n")
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    assert report["parse_summary"]["process_snapshots"] == 5


def test_large_exfil_byte_count_uses_int64(binary: Path, tmp_path: Path) -> None:
    """Large exfiltration byte counts are handled without 32-bit overflow."""
    bundle = copy_bundle(tmp_path)
    base = (bundle / "network" / "egress.log").read_text(encoding="utf-8").splitlines()[0]
    row = kv_pairs(base)
    large_bytes = 3_000_000_000
    with (bundle / "network" / "egress.log").open("a", encoding="utf-8") as f:
        f.write(base.replace("bytes=" + row["bytes"], f"bytes={large_bytes}") + "\n")
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    assert report["exfiltration"]["bytes"] == large_bytes
    assert report["exfiltration"]["destination_ip"] == row["dst"]


def test_remediation_blocks_ip_iocs(binary: Path, tmp_path: Path) -> None:
    """Remediation actions block intrusion-related IP indicators."""
    bundle = copy_bundle(tmp_path)
    report, _ = run_ok(binary, bundle, tmp_path / "out")
    remediation = read_json(tmp_path / "out" / "remediation_plan.json")
    for ioc in report["iocs"]:
        if ioc.startswith("ip:"):
            assert f"block_{ioc}" in remediation["actions"]


def test_artifacts_are_newline_terminated(binary: Path, tmp_path: Path) -> None:
    """Text and CSV artifacts are newline-terminated for POSIX tooling."""
    bundle = copy_bundle(tmp_path)
    out = tmp_path / "out"
    assert run_cli(binary, bundle, out).returncode == 0
    assert (out / "attack_timeline.csv").read_bytes().endswith(b"\n")
    assert (out / "iocs.txt").read_bytes().endswith(b"\n")


def test_incident_report_has_no_floating_numbers(binary: Path, tmp_path: Path) -> None:
    """All numeric fields in the report are JSON integers (no floats)."""
    report, _ = run_ok(binary, copy_bundle(tmp_path), tmp_path / "out")
    def walk(value: Any, path: str) -> None:
        if isinstance(value, float):
            raise AssertionError(f"float not allowed at {path}: {value!r}")
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, f"{path}.{k}")
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{path}[{i}]")

    walk(report, "$")


def test_archive_escape_rejects_absolute_member(binary: Path, tmp_path: Path) -> None:
    """Absolute zip member paths reject with archive_escape."""
    bundle = copy_bundle(tmp_path)
    write_archive(bundle, {"/abs/path": b"bad"})
    assert_rejected(binary, bundle, tmp_path / "out", "archive_escape")


def test_archive_escape_rejects_backslash_traversal(binary: Path, tmp_path: Path) -> None:
    """Zip members using backslash traversal reject with archive_escape."""
    bundle = copy_bundle(tmp_path)
    write_archive(bundle, {"..\\escape": b"bad"})
    assert_rejected(binary, bundle, tmp_path / "out", "archive_escape")
