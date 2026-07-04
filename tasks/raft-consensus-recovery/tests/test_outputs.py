from __future__ import annotations

import brotli
import json
import os
import struct
import subprocess
from pathlib import Path


APP = Path(os.environ.get("APP_DIR", "/app"))


def make_command(
    index: int,
    *,
    term: int = 1,
    tick: int | None = None,
    node_id: str = "n1",
    op: str = "set",
    key: str = "quota",
    value: str = "100",
) -> dict[str, object]:
    return {
        "index": index,
        "term": term,
        "tick": tick if tick is not None else index * 10,
        "node_id": node_id,
        "command": {"op": op, "key": key, "value": value},
    }


def encoded_line(obj: dict[str, object], *, encoding: str = "base64+json") -> dict[str, str]:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if encoding == "base64+brotli+json":
        payload = brotli.compress(payload)
    script = (
        "const fs=require('node:fs');"
        "const zlib=require('node:zlib');"
        "let b=fs.readFileSync(0);"
        f"if ({json.dumps(encoding)} === 'base64+gzip+json') b=zlib.gzipSync(b);"
        "process.stdout.write(b.toString('base64'));"
    )
    encoded = subprocess.run(
        ["node", "-e", script],
        input=payload,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.decode("ascii")
    return {
        "encoding": encoding,
        "payload": encoded,
    }


def write_wal_frames(path: Path, commands: list[dict[str, object]]) -> None:
    payload = bytearray()
    for cmd in commands:
        data = json.dumps(cmd, sort_keys=True, separators=(",", ":")).encode()
        payload.extend(struct.pack(">I", len(data)))
        payload.extend(data)
    path.write_bytes(bytes(payload))


def write_env_dir(root: Path, files: dict[str, str] | None = None) -> None:
    env_dir = root / "env.d"
    env_dir.mkdir(parents=True, exist_ok=True)
    if files is None:
        files = {
            "01-app.env": "RAFT_ENV=production\nSIMULATION_SEED=42\n",
        }
    for name, content in files.items():
        (env_dir / name).write_text(content, encoding="utf-8")


def write_bundle(
    root: Path,
    commands: list[dict[str, object] | dict[str, str]],
    *,
    partitions: list[dict[str, object]] | None = None,
    rpc: list[dict[str, object]] | None = None,
    cluster: dict[str, object] | None = None,
    snapshots: list[str] | None = None,
    env_files: dict[str, str] | None = None,
    bom: bool = False,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    scenario = APP / "scenarios" / "partition"
    with (root / "wal_entries.jsonl").open("wb") as handle:
        if bom:
            handle.write(b"\xef\xbb\xbf")
        for item in commands:
            handle.write(json.dumps(item, sort_keys=True, separators=(",", ":")).encode())
            handle.write(b"\n")
    plain_cmds = []
    for item in commands:
        if "encoding" in item:
            enc = str(item["encoding"])
            script = (
                "const fs=require('node:fs');"
                "const zlib=require('node:zlib');"
                "let b=Buffer.from(fs.readFileSync(0).toString(), 'base64');"
                f"if ({json.dumps(enc)} === 'base64+gzip+json') b=zlib.gunzipSync(b);"
                "process.stdout.write(b);"
            )
            raw = subprocess.run(
                ["node", "-e", script],
                input=str(item["payload"]).encode("ascii"),
                stdout=subprocess.PIPE,
                check=True,
            ).stdout
            if enc == "base64+brotli+json":
                raw = brotli.decompress(raw)
            plain_cmds.append(json.loads(raw.decode()))
        else:
            plain_cmds.append(item)
    frame_order = sorted(plain_cmds, key=lambda c: (int(c["tick"]), int(c["index"]), str(c["node_id"])))
    write_wal_frames(root / "wal_frames.bin", frame_order)
    if partitions is None:
        partitions = [
            {"tick": 80, "kind": "partition", "isolated": ["n4", "n5"], "majority": ["n1", "n2", "n3"]},
            {"tick": 120, "kind": "heal"},
        ]
    with (root / "partition_events.jsonl").open("w", encoding="utf-8") as handle:
        for row in partitions:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    if rpc is None:
        rpc = [
            {"tick": 15, "type": "RequestVote", "from": "n2", "to": "n1", "term": 1, "last_log_index": 1, "last_log_term": 1, "granted": True},
            {"tick": 100, "type": "RequestVote", "from": "n1", "to": "n2", "term": 2, "last_log_index": 5, "last_log_term": 2, "granted": True},
        ]
    with (root / "rpc_trace.jsonl").open("w", encoding="utf-8") as handle:
        for row in rpc:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    if cluster is None:
        cluster = {"nodes": ["n1", "n2", "n3", "n4", "n5"], "quorum_size": 3, "election_timeout_ms": 150}
    (root / "cluster.json").write_text(json.dumps(cluster, indent=2) + "\n", encoding="utf-8")
    (root / "election_timeouts.json").write_text(
        (scenario / "election_timeouts.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    if snapshots is None:
        snapshots = [
            "node_id,last_included_index,last_included_term,checksum",
            "n1,6,2,a1b2c3",
            "n2,6,2,a1b2c3",
        ]
    (root / "snapshots.csv").write_text("\n".join(snapshots) + "\n", encoding="utf-8")
    (root / "forensics_notes.txt").write_text("notes\n", encoding="utf-8")
    write_env_dir(root, env_files)
    return root


def run_cli(bundle: Path, output: Path, *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "node",
            str(APP / "consensus_lab" / "cli.js"),
            "--bundle",
            str(bundle),
            "--output",
            str(output),
        ],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_commands() -> list[dict[str, object]]:
    return [
        make_command(1, term=1, tick=10, value="100"),
        make_command(2, term=1, tick=20, key="session", value="s1"),
        make_command(3, term=1, tick=30, value="200"),
        make_command(4, term=2, tick=90, value="300"),
        make_command(5, term=2, tick=95, key="session", value="s2"),
        make_command(4, term=3, tick=92, node_id="n4", value="999"),
        make_command(6, term=3, tick=130, key="leader", value="n1"),
        make_command(7, term=3, tick=135, node_id="n2", key="replica", value="n2"),
        make_command(8, term=3, tick=140, node_id="n1", op="del", key="temp", value=""),
    ]


def pressure_commands(count: int = 256) -> list[dict[str, object] | dict[str, str]]:
    commands: list[dict[str, object] | dict[str, str]] = []
    for index in range(1, count + 1):
        commands.append(
            make_command(
                index,
                term=1 + (index // 64),
                tick=index * 5,
                key=f"key-{index:04d}",
                value=str(index),
            )
        )
    commands[7] = encoded_line(make_command(8, term=1, tick=40, key="encoded", value="x"))
    commands[11] = encoded_line(make_command(12, term=1, tick=60), encoding="base64+gzip+json")
    commands[15] = encoded_line(make_command(16, term=1, tick=80), encoding="base64+brotli+json")
    commands.append(dict(commands[20]))
    return commands


def test_consensus_split_brain_recovery_on_default_partition(tmp_path: Path) -> None:
    """The default partition bundle must classify split brain and restore consensus safety."""
    bundle = APP / "scenarios" / "partition"
    output = tmp_path / "out"
    before_conf = (APP / "config" / "cluster_policy.json").read_bytes()

    result = run_cli(bundle, output)

    assert result.returncode == 0, result.stderr
    assert (APP / "config" / "cluster_policy.json").read_bytes() == before_conf
    report = read_json(output / "consensus_report.json")
    assert report["status"] == "accepted"
    assert report["schema_version"] == 4
    assert report["classification"] == "raft_split_brain"
    assert report["root_cause"] == "raft_split_brain"
    assert report["primary_node"] == "n1"
    assert report["before"]["split_brain_detected"] is True
    assert report["after"]["split_brain_detected"] is False
    assert report["before"]["commands_lost"] >= 1
    assert report["after"]["commands_lost"] == 0
    assert report["after"]["commands_committed"] >= 4
    cert = read_json(output / "safety_certificate.json")
    assert cert["split_brain_detected"] is False
    assert all(item["passed"] for item in cert["invariants"])
    trace = read_json(output / "command_trace.json")
    assert trace["schema_version"] == 4
    assert isinstance(trace["commands"], list)
    timeline = (output / "term_timeline.csv").read_text(encoding="utf-8").strip().splitlines()
    assert timeline[0] == "phase,node_id,term,start_tick,end_tick,role,votes_received"
    assert any(row.startswith("before,") for row in timeline[1:])
    assert any(row.startswith("after,") for row in timeline[1:])
    manifest = (output / "wal_digest.txt").read_text(encoding="utf-8").splitlines()
    assert manifest == sorted(manifest)
    assert "cluster_policy_changed=false" in manifest
    assert any(line.startswith("linearizability_digest=") for line in manifest)
    assert any(line.startswith("simulation_seed=") for line in manifest)


def test_pressure_bundle_restores_consensus(tmp_path: Path) -> None:
    """A large mixed command stream must restore linearizable commits after remediation."""
    bundle = write_bundle(tmp_path / "bundle", pressure_commands())
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode == 0
    report = read_json(output / "consensus_report.json")
    assert report["classification"] == "raft_split_brain"
    assert report["after"]["split_brain_detected"] is False
    assert report["after"]["commands_committed"] > 200
    assert report["parse_summary"]["accepted_commands"] == 256
    assert report["parse_summary"]["duplicate_commands"] == 1


def test_order_independent_linearizability_digest(tmp_path: Path) -> None:
    """Equivalent command sets in different orders must keep the same digest and after metrics."""
    original = pressure_commands(count=128)
    shuffled = list(reversed(original[::2])) + list(reversed(original[1::2]))
    bundle_a = write_bundle(tmp_path / "a", original)
    bundle_b = write_bundle(tmp_path / "b", shuffled)
    out_a = tmp_path / "1"
    out_b = tmp_path / "2"
    assert run_cli(bundle_a, out_a).returncode == 0
    assert run_cli(bundle_b, out_b).returncode == 0
    report_a = read_json(out_a / "consensus_report.json")
    report_b = read_json(out_b / "consensus_report.json")
    assert report_a["linearizability_digest"] == report_b["linearizability_digest"]
    assert report_a["after"] == report_b["after"]


def test_repeated_runs_byte_identical(tmp_path: Path) -> None:
    """Two consecutive replays must emit identical artifact bytes."""
    bundle = write_bundle(tmp_path / "bundle", pressure_commands(count=64))
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    assert run_cli(bundle, out_a).returncode == 0
    assert run_cli(bundle, out_b).returncode == 0
    for name in (
        "consensus_report.json",
        "term_timeline.csv",
        "command_trace.json",
        "safety_certificate.json",
        "wal_digest.txt",
    ):
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes()


def test_failure_priority_node_id_invalid(tmp_path: Path) -> None:
    """Invalid node ids must outrank duplicate entry conflicts."""
    bad = make_command(1)
    bad["node_id"] = "INVALID NODE!"
    dup_a = make_command(2)
    dup_b = make_command(2)
    dup_b["command"]["value"] = "999"
    bundle = write_bundle(tmp_path / "bundle", [bad, dup_a, dup_b])
    output = tmp_path / "out"
    result = run_cli(bundle, output)
    assert result.returncode != 0
    report = read_json(output / "consensus_report.json")
    assert report["status"] == "rejected"
    assert report["error"]["code"] == "node_id_invalid"
    assert not (output / "command_trace.json").exists()


def test_duplicate_entry_rejected(tmp_path: Path) -> None:
    """Duplicate index/term pairs with conflicting payloads must reject."""
    first = make_command(1)
    second = make_command(1)
    second["command"]["value"] = "999"
    bundle = write_bundle(tmp_path / "bundle", [first, second])
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "duplicate_entry"


def test_log_index_gap_rejected(tmp_path: Path) -> None:
    """Gaps within a node term log must reject."""
    first = make_command(1, term=2, node_id="n1")
    second = make_command(3, term=2, node_id="n1")
    bundle = write_bundle(tmp_path / "bundle", [first, second])
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "log_index_gap"


def test_term_overflow_rejected(tmp_path: Path) -> None:
    """Terms above the maximum must reject."""
    bad = make_command(1, term=2147483648)
    bundle = write_bundle(tmp_path / "bundle", [bad])
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "term_overflow"


def test_rpc_term_stale_rejected(tmp_path: Path) -> None:
    """RPC terms below correlated WAL terms must reject."""
    rpc = [
        {"tick": 10, "type": "RequestVote", "from": "n2", "to": "n1", "term": 0, "last_log_index": 1, "last_log_term": 1, "granted": True},
    ]
    bundle = write_bundle(tmp_path / "bundle", [make_command(1, tick=10)], rpc=rpc)
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "rpc_term_stale"


def test_rpc_term_stale_outranks_bad_encoding(tmp_path: Path) -> None:
    """RPC staleness must outrank malformed wrapped WAL lines."""
    rpc = [
        {"tick": 10, "type": "RequestVote", "from": "n2", "to": "n1", "term": 0, "last_log_index": 1, "last_log_term": 1, "granted": True},
    ]
    bundle = write_bundle(tmp_path / "bundle", [make_command(1, tick=10)], rpc=rpc)
    with (bundle / "wal_entries.jsonl").open("a", encoding="utf-8") as handle:
        handle.write('{"encoding":"base64+zip+json","payload":"e30="}\n')
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "rpc_term_stale"


def test_rpc_order_violation_rejected(tmp_path: Path) -> None:
    """RPC term regression for the same pair must reject."""
    rpc = [
        {"tick": 10, "type": "RequestVote", "from": "n2", "to": "n1", "term": 3, "last_log_index": 1, "last_log_term": 1, "granted": True},
        {"tick": 20, "type": "RequestVote", "from": "n2", "to": "n1", "term": 2, "last_log_index": 2, "last_log_term": 1, "granted": True},
    ]
    bundle = write_bundle(tmp_path / "bundle", [make_command(1), make_command(2, tick=20)], rpc=rpc)
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "rpc_order_violation"


def test_snapshot_conflict_rejected(tmp_path: Path) -> None:
    """Colliding snapshot rows must reject."""
    rows = [
        "node_id,last_included_index,last_included_term,checksum",
        "n1,6,2,a1b2c3",
        "n1,6,3,deadbeef",
    ]
    bundle = write_bundle(tmp_path / "bundle", [make_command(1)], snapshots=rows)
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "snapshot_conflict"


def test_config_quorum_invalid_rejected(tmp_path: Path) -> None:
    """Invalid quorum sizes must reject."""
    cluster = {"nodes": ["n1", "n2", "n3", "n4", "n5"], "quorum_size": 2}
    bundle = write_bundle(tmp_path / "bundle", [make_command(1)], cluster=cluster)
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "config_quorum_invalid"


def test_partition_overlap_rejected(tmp_path: Path) -> None:
    """Overlapping partition isolation windows must reject."""
    partitions = [
        {"tick": 50, "kind": "partition", "isolated": ["n4"], "majority": ["n1", "n2", "n3", "n5"]},
        {"tick": 60, "kind": "partition", "isolated": ["n4"], "majority": ["n1", "n2", "n3", "n5"]},
    ]
    bundle = write_bundle(tmp_path / "bundle", [make_command(1)], partitions=partitions)
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "partition_overlap"


def test_env_not_production_rejected(tmp_path: Path) -> None:
    """Non-production env must reject."""
    env_files = {"01-app.env": "RAFT_ENV=staging\n"}
    bundle = write_bundle(tmp_path / "bundle", [make_command(1)], env_files=env_files)
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "env_not_production"


def test_wal_order_violation_rejected(tmp_path: Path) -> None:
    """Out-of-order WAL frame ticks must reject."""
    cmds = [make_command(1, tick=30), make_command(2, tick=10)]
    bundle = write_bundle(tmp_path / "bundle", cmds)
    write_wal_frames(bundle / "wal_frames.bin", [cmds[0], cmds[1]])
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "wal_order_violation"


def test_empty_stream_rejected(tmp_path: Path) -> None:
    """Empty command streams must reject with no_valid_commands."""
    bundle = write_bundle(tmp_path / "bundle", [])
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "no_valid_commands"


def test_utf8_bom_stripped(tmp_path: Path) -> None:
    """UTF-8 BOM on first WAL line must not break parsing."""
    bundle = write_bundle(tmp_path / "bundle", [make_command(1)], bom=True)
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode == 0


def test_large_pressure_trace_efficient(tmp_path: Path) -> None:
    """Replay must stay efficient on a 4000-command pressure stream."""
    bundle = write_bundle(tmp_path / "bundle", pressure_commands(count=4000))
    output = tmp_path / "out"
    result = run_cli(bundle, output, timeout=45)
    assert result.returncode == 0, result.stderr
    report = read_json(output / "consensus_report.json")
    assert report["parse_summary"]["accepted_commands"] == 4000
    assert report["parse_summary"]["duplicate_commands"] == 1
    assert report["after"]["commands_committed"] > 3000


def test_command_trace_sorted_and_complete(tmp_path: Path) -> None:
    """Command trace entries must be sorted by key with stage lists."""
    bundle = write_bundle(tmp_path / "bundle", default_commands())
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode == 0
    trace = read_json(output / "command_trace.json")
    assert trace["schema_version"] == 4
    keys = [item["key"] for item in trace["commands"]]
    assert keys == sorted(keys)
    for item in trace["commands"]:
        assert item["stages"] == sorted(item["stages"])
    assert "quota" in keys
    assert "session" in keys


def test_node_id_invalid_outranks_duplicate_entry(tmp_path: Path) -> None:
    """Invalid keys must reject with node_id_invalid before duplicate checks."""
    bad = make_command(1)
    bad["command"]["key"] = ""
    dup = make_command(1)
    dup["command"]["value"] = "other"
    bundle = write_bundle(tmp_path / "bundle", [bad, dup])
    output = tmp_path / "out"
    assert run_cli(bundle, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "node_id_invalid"


def test_bundle_incomplete_rejected(tmp_path: Path) -> None:
    """Missing required bundle files must reject."""
    root = tmp_path / "bundle"
    root.mkdir()
    (root / "cluster.json").write_text('{"nodes":["n1"],"quorum_size":1}\n', encoding="utf-8")
    output = tmp_path / "out"
    assert run_cli(root, output).returncode != 0
    assert read_json(output / "consensus_report.json")["error"]["code"] == "bundle_incomplete"
