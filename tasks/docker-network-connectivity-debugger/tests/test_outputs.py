"""Verification for docker-network-connectivity-debugger (Go replayer + CNX1 capture decoder)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path
from typing import Any

import pytest

REPORT_PATH = Path("/app/build/docker_network_connectivity_debugger_report.json")
REPORT_FIRST = Path("/logs/verifier/report_first.json")
VERIFIER_DIR = Path("/logs/verifier")
DATA_DIR = Path("/app/data")
MANIFEST_PATH = DATA_DIR / "docker_network_connectivity_debugger_manifest.json"
APP_DIR = Path("/app")
BINARY = APP_DIR / "build" / "docker-network-connectivity-debugger"
CAPTURE_NAME = "docker_network_connectivity_debugger_capture.cnx"

GOLDEN_REPORT_SHA256 = (
    "f05ba1885421fc07be82179a16085aa15306e7618ccb8c0dc21752d5ec536f48"
)

AUDIT_KINDS = frozenset(
    {"BRIDGE_GAP", "OVERLAY_ASYMMETRY", "OPEN_DMZ_PATH", "INSPECT_UNBOUND"}
)

def _sort_key(ev: dict[str, Any]) -> str:
    kind = ev["kind"]
    if kind in ("ALLOW_EGRESS", "REVOKE_EGRESS"):
        return ev.get("to_container", "")
    if kind == "CONNECT_PROBE":
        return ev.get("target_id", "")
    if kind == "CREATE_NETWORK":
        return ev.get("network_id", "")
    return ev.get("container_id", "")


def _port_key(port: int, protocol: str) -> str:
    proto = protocol or "tcp"
    return f"{port}/{proto}"


def _connectivity_risk(zone: str) -> str:
    if zone == "edge":
        return "elevated"
    if zone == "dmz":
        return "critical"
    return "none"


def _finding_id(scenario_id: str, entity_id: str, seq: int) -> str:
    return f"{scenario_id}::{entity_id}::{seq:04d}"


def _resolve_bools(
    require_shared: bool,
    block_edge: bool,
    require_tls: bool,
    overrides: dict[str, Any] | None,
) -> tuple[bool, bool, bool]:
    if not overrides:
        return require_shared, block_edge, require_tls
    if "require_shared_network" in overrides:
        v = overrides["require_shared_network"]
        if isinstance(v, bool):
            require_shared = v
    if "block_edge_to_internal" in overrides:
        v = overrides["block_edge_to_internal"]
        if isinstance(v, bool):
            block_edge = v
    if "require_tls_on_internal" in overrides:
        v = overrides["require_tls_on_internal"]
        if isinstance(v, bool):
            require_tls = v
    return require_shared, block_edge, require_tls


def _shared_networks(members: dict[str, set[str]], src: str, tgt: str) -> list[str]:
    src_nets = members.get(src)
    tgt_nets = members.get(tgt)
    if not src_nets or not tgt_nets:
        return []
    return sorted(src_nets & tgt_nets)


def _dns_ok(
    dns: dict[str, dict[str, str]],
    nets: list[str],
    alias: str,
    target: str,
) -> bool:
    for net in nets:
        by_net = dns.get(net, {})
        if by_net.get(alias) == target:
            return True
    return False


def analyze_scenario(cfg: dict[str, Any], events: list[dict[str, Any]], cap: dict[str, int]) -> dict[str, Any]:
    """Replay one scenario and return a schema-shaped scenario row."""
    scenario_id = cfg["scenario_id"]
    require_shared = cfg.get("require_shared_network", True)
    block_edge = cfg.get("block_edge_to_internal", True)
    require_tls = cfg.get("require_tls_on_internal", True)
    require_shared, block_edge, require_tls = _resolve_bools(
        require_shared,
        block_edge,
        require_tls,
        cfg.get("policy_overrides"),
    )

    containers: dict[str, dict[str, Any]] = {}
    networks: dict[str, str] = {}
    network_order: list[str] = []
    members: dict[str, set[str]] = {}
    dns: dict[str, dict[str, str]] = {}
    egress: set[str] = set()
    findings: list[dict[str, Any]] = []
    dup_skipped = 0
    seen_event: set[str] = set()
    max_seq = 0

    ordered = sorted(
        events,
        key=lambda ev: (ev["seq"], _sort_key(ev), ev.get("event_id", "")),
    )

    for ev in ordered:
        seq = int(ev["seq"])
        if seq > max_seq:
            max_seq = seq
        kind = ev["kind"]
        event_id = ev.get("event_id", "")
        if event_id:
            if event_id in seen_event:
                dup_skipped += 1
                continue
            seen_event.add(event_id)

        if kind == "REGISTER_CONTAINER":
            cid = ev["container_id"]
            if cid in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, cid, seq),
                        "entity_id": cid,
                        "kind": "DUPLICATE_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": "",
                    }
                )
                continue
            containers[cid] = {"zone": ev["zone"], "labels": set(), "published_ports": set()}
            members[cid] = set()

        elif kind == "CREATE_NETWORK":
            nid = ev["network_id"]
            if nid in networks:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, nid, seq),
                        "entity_id": nid,
                        "kind": "DUPLICATE_NETWORK",
                        "event_seq": seq,
                        "operation": "",
                        "detail": "",
                    }
                )
                continue
            networks[nid] = ev["driver"]
            network_order.append(nid)
            dns[nid] = {}

        elif kind == "JOIN_NETWORK":
            cid = ev["container_id"]
            nid = ev["network_id"]
            if cid not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, cid, seq),
                        "entity_id": cid,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            if nid not in networks:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, nid, seq),
                        "entity_id": nid,
                        "kind": "UNKNOWN_NETWORK",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            if nid in members[cid]:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, cid, seq),
                        "entity_id": cid,
                        "kind": "DUPLICATE_JOIN",
                        "event_seq": seq,
                        "operation": "",
                        "detail": nid,
                    }
                )
                continue
            members[cid].add(nid)
            alias = ev.get("alias", "")
            if alias:
                dns[nid][alias] = cid

        elif kind == "LEAVE_NETWORK":
            cid = ev["container_id"]
            nid = ev["network_id"]
            if cid not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, cid, seq),
                        "entity_id": cid,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            if nid not in networks:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, nid, seq),
                        "entity_id": nid,
                        "kind": "UNKNOWN_NETWORK",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            if nid in members.get(cid, set()):
                members[cid].discard(nid)
                for alias, target in list(dns.get(nid, {}).items()):
                    if target == cid:
                        del dns[nid][alias]

        elif kind == "PUBLISH_PORT":
            cid = ev["container_id"]
            if cid not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, cid, seq),
                        "entity_id": cid,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            containers[cid]["published_ports"].add(_port_key(int(ev["port"]), ev.get("protocol", "")))

        elif kind == "BIND_LABEL":
            cid = ev["container_id"]
            if cid not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, cid, seq),
                        "entity_id": cid,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            label = ev.get("label", "")
            if label:
                containers[cid]["labels"].add(label)

        elif kind == "ALLOW_EGRESS":
            from_c = ev["from_container"]
            to_c = ev["to_container"]
            if from_c not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, from_c, seq),
                        "entity_id": from_c,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            if to_c not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, to_c, seq),
                        "entity_id": to_c,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            key = f"{from_c}\x00{to_c}"
            if key in egress:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, to_c, seq),
                        "entity_id": to_c,
                        "kind": "DUPLICATE_EGRESS",
                        "event_seq": seq,
                        "operation": "",
                        "detail": from_c,
                    }
                )
                continue
            egress.add(key)

        elif kind == "REVOKE_EGRESS":
            from_c = ev["from_container"]
            to_c = ev["to_container"]
            if from_c not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, from_c, seq),
                        "entity_id": from_c,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            if to_c not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, to_c, seq),
                        "entity_id": to_c,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            egress.discard(f"{from_c}\x00{to_c}")

        elif kind == "REGISTER_DNS":
            nid = ev["network_id"]
            cid = ev["container_id"]
            if nid not in networks:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, nid, seq),
                        "entity_id": nid,
                        "kind": "UNKNOWN_NETWORK",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            if cid not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, cid, seq),
                        "entity_id": cid,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            dns[nid][ev["alias"]] = cid

        elif kind == "CONNECT_PROBE":
            src = ev["source_id"]
            tgt = ev["target_id"]
            proto = ev.get("protocol") or "tcp"
            op = proto.upper()
            if tgt not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, tgt, seq),
                        "entity_id": tgt,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            if src not in containers:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, src, seq),
                        "entity_id": src,
                        "kind": "UNKNOWN_CONTAINER",
                        "event_seq": seq,
                        "operation": "",
                        "detail": kind,
                    }
                )
                continue
            tgt_st = containers[tgt]
            src_st = containers[src]
            dns_alias = ev.get("dns_alias", "")
            if dns_alias:
                nets = _shared_networks(members, src, tgt)
                if not _dns_ok(dns, nets, dns_alias, tgt):
                    findings.append(
                        {
                            "finding_id": _finding_id(scenario_id, src, seq),
                            "entity_id": src,
                            "kind": "DNS_UNRESOLVED",
                            "event_seq": seq,
                            "operation": op,
                            "detail": dns_alias,
                        }
                    )
                    continue
            if require_shared and not _shared_networks(members, src, tgt):
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, tgt, seq),
                        "entity_id": tgt,
                        "kind": "NETWORK_PARTITION",
                        "event_seq": seq,
                        "operation": op,
                        "detail": src,
                    }
                )
                continue
            pk = _port_key(int(ev["port"]), ev.get("protocol", ""))
            if pk not in tgt_st["published_ports"]:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, tgt, seq),
                        "entity_id": tgt,
                        "kind": "PORT_UNPUBLISHED",
                        "event_seq": seq,
                        "operation": op,
                        "detail": pk,
                    }
                )
                continue
            if f"{src}\x00{tgt}" not in egress:
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, tgt, seq),
                        "entity_id": tgt,
                        "kind": "EGRESS_DENIED",
                        "event_seq": seq,
                        "operation": op,
                        "detail": src,
                    }
                )
                continue
            if block_edge and src_st["zone"] == "edge" and tgt_st["zone"] == "internal":
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, src, seq),
                        "entity_id": src,
                        "kind": "ZONE_BLOCKED",
                        "event_seq": seq,
                        "operation": op,
                        "detail": tgt,
                    }
                )
                continue
            if (
                require_tls
                and tgt_st["zone"] == "internal"
                and "net:tls" in tgt_st["labels"]
                and not ev.get("use_tls", False)
            ):
                findings.append(
                    {
                        "finding_id": _finding_id(scenario_id, tgt, seq),
                        "entity_id": tgt,
                        "kind": "TLS_REQUIRED",
                        "event_seq": seq,
                        "operation": op,
                        "detail": "",
                    }
                )
                continue

    audit_seq = max_seq + 1
    bridge_flagged: set[str] = set()
    overlay_flagged: set[str] = set()
    open_flagged: set[str] = set()
    inspect_flagged: set[str] = set()

    for nid in network_order:
        if networks.get(nid) != "bridge":
            continue
        edge_on: list[str] = []
        internal_on: list[str] = []
        for cid, nets in members.items():
            if nid not in nets:
                continue
            zone = containers[cid]["zone"]
            if zone == "edge":
                edge_on.append(cid)
            if zone == "internal":
                internal_on.append(cid)
        edge_on.sort()
        internal_on.sort()
        for edge_c in edge_on:
            for int_c in internal_on:
                bkey = f"{edge_c}::{int_c}"
                if bkey in bridge_flagged:
                    continue
                if f"{edge_c}\x00{int_c}" not in egress:
                    bridge_flagged.add(bkey)
                    findings.append(
                        {
                            "finding_id": _finding_id(scenario_id, int_c, audit_seq),
                            "entity_id": int_c,
                            "kind": "BRIDGE_GAP",
                            "event_seq": audit_seq,
                            "operation": "",
                            "detail": edge_c,
                        }
                    )

    for nid in network_order:
        if networks.get(nid) != "overlay":
            continue
        if nid in overlay_flagged:
            continue
        edge_on = []
        internal_on = []
        for cid, nets in members.items():
            if nid not in nets:
                continue
            zone = containers[cid]["zone"]
            if zone == "edge":
                edge_on.append(cid)
            if zone == "internal":
                internal_on.append(cid)
        if not edge_on or not internal_on:
            continue
        edge_on.sort()
        internal_on.sort()
        has_internal_to_edge = False
        for int_c in internal_on:
            for edge_c in edge_on:
                if f"{int_c}\x00{edge_c}" in egress:
                    has_internal_to_edge = True
                    break
            if has_internal_to_edge:
                break
        if not has_internal_to_edge:
            overlay_flagged.add(nid)
            findings.append(
                {
                    "finding_id": _finding_id(scenario_id, internal_on[0], audit_seq),
                    "entity_id": internal_on[0],
                    "kind": "OVERLAY_ASYMMETRY",
                    "event_seq": audit_seq,
                    "operation": "",
                    "detail": edge_on[0],
                }
            )

    for cid, st in sorted(containers.items()):
        if st["zone"] != "dmz" or not st["published_ports"]:
            continue
        if "net:inspect" in st["labels"]:
            continue
        if cid not in open_flagged:
            open_flagged.add(cid)
            ports = sorted(st["published_ports"])
            findings.append(
                {
                    "finding_id": _finding_id(scenario_id, cid, audit_seq),
                    "entity_id": cid,
                    "kind": "OPEN_DMZ_PATH",
                    "event_seq": audit_seq,
                    "operation": "",
                    "detail": ports[0],
                }
            )

    for cid, st in sorted(containers.items()):
        if st["zone"] != "dmz":
            continue
        if "net:inspect" in st["labels"]:
            continue
        has_edge_inbound = False
        for key in egress:
            parts = key.split("\x00", 1)
            if len(parts) != 2 or parts[1] != cid:
                continue
            src_st = containers.get(parts[0])
            if src_st and src_st["zone"] == "edge":
                has_edge_inbound = True
                break
        if has_edge_inbound and cid not in inspect_flagged:
            inspect_flagged.add(cid)
            findings.append(
                {
                    "finding_id": _finding_id(scenario_id, cid, audit_seq),
                    "entity_id": cid,
                    "kind": "INSPECT_UNBOUND",
                    "event_seq": audit_seq,
                    "operation": "",
                    "detail": "",
                }
            )

    egress_out = sorted(
        [{"from_container": k.split("\x00", 1)[0], "to_container": k.split("\x00", 1)[1]} for k in egress],
        key=lambda e: (e["from_container"], e["to_container"]),
    )
    out_containers = []
    for cid in sorted(containers):
        st = containers[cid]
        out_containers.append(
            {
                "container_id": cid,
                "zone": st["zone"],
                "labels": sorted(st["labels"]),
                "published_ports": sorted(st["published_ports"]),
                "connectivity_risk": _connectivity_risk(st["zone"]),
            }
        )
    findings.sort(key=lambda f: f["finding_id"])
    status = "VALID" if not findings else "INVALID"

    return {
        "scenario_id": scenario_id,
        "status": status,
        "duplicate_events_skipped": dup_skipped,
        "capture": cap,
        "egress_rules": egress_out,
        "containers": out_containers,
        "findings": findings,
    }


def build_reference_report(
    data_dir: Path,
    manifest: dict[str, Any],
    decode_capture: Any,
) -> dict[str, Any]:
    """Build full report from bundled fixtures using an injected CNX1 decoder."""
    scenarios: list[dict[str, Any]] = []
    for sid in manifest["scenarios"]:
        cfg = json.loads((data_dir / f"{sid}.json").read_text(encoding="utf-8"))
        cap_path = data_dir / sid / "docker_network_connectivity_debugger_capture.cnx"
        stats, events = decode_capture(cap_path)
        cap = {k: stats[k] for k in (
            "format_version",
            "records_total",
            "records_valid",
            "records_rejected",
            "dup_seq_rejects",
            "truncated_tail",
            "payload_bytes",
        )}
        scenarios.append(analyze_scenario(cfg, events, cap))
    return {"scenarios": scenarios}


def decode_capture_bytes(data: bytes) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """Decode CNX1 little-endian capture per DOCKER_NETWORK_CONNECTIVITY_DEBUGGER_CAPTURE_FORMAT.md."""
    if len(data) < 8 or data[:4] != b"CNX1":
        raise ValueError("bad magic")
    format_version = struct.unpack_from("<I", data, 4)[0]
    stats: dict[str, int] = {
        "format_version": format_version,
        "records_total": 0,
        "records_valid": 0,
        "records_rejected": 0,
        "dup_seq_rejects": 0,
        "truncated_tail": 0,
        "payload_bytes": 0,
    }
    if format_version != 1:
        raise ValueError("unsupported format_version")
    off = 8
    seen: set[int] = set()
    events: list[dict[str, Any]] = []
    while off < len(data):
        if off + 12 > len(data):
            stats["records_rejected"] += 1
            stats["truncated_tail"] = 1
            break
        record_seq, flags, reserved, plen = struct.unpack_from("<I H H I", data, off)
        off += 12
        stats["records_total"] += 1
        reason = ""
        if reserved != 0:
            reason = "BAD_RESERVED"
        elif flags != 0:
            reason = "BAD_FLAGS"
        elif plen > 4096:
            reason = "LEN_OVERFLOW"
        elif record_seq in seen:
            reason = "DUP_SEQ"
        if reason == "LEN_OVERFLOW":
            if off + plen + 4 <= len(data):
                off += plen + 4
                stats["records_rejected"] += 1
                seen.add(record_seq)
                continue
            stats["records_rejected"] += 1
            stats["truncated_tail"] = 1
            break
        if off + plen + 4 > len(data):
            stats["records_rejected"] += 1
            stats["truncated_tail"] = 1
            break
        payload = data[off : off + plen]
        off += plen
        checksum = struct.unpack_from("<I", data, off)[0]
        off += 4
        if reason == "":
            hdr = struct.pack("<I H H I", record_seq, flags, reserved, plen)
            if zlib.crc32(hdr + payload) & 0xFFFFFFFF != checksum:
                reason = "BAD_CRC"
        seen.add(record_seq)
        if reason:
            stats["records_rejected"] += 1
            if reason == "DUP_SEQ":
                stats["dup_seq_rejects"] += 1
            continue
        events.append(json.loads(payload.decode("utf-8")))
        stats["records_valid"] += 1
        stats["payload_bytes"] += plen
    return stats, events


def decode_capture(path: Path) -> tuple[dict[str, int], list[dict[str, Any]]]:
    return decode_capture_bytes(path.read_bytes())


def _go_capture_probe(path: str, mode: str) -> str:
    probe_dir = APP_DIR / "cmd" / "decodeprobe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    escaped = path.replace("\\", "\\\\").replace('"', '\\"')
    if mode == "err":
        body = (
            f'\t_, _, err := capture.Decode("{escaped}")\n'
            "\tif err != nil {\n"
            '\t\tfmt.Println(err.Error())\n'
            "\t}"
        )
        source = (
            "package main\n\nimport (\n"
            '\t"fmt"\n'
            '\tcapture "docker-network-connectivity-debugger/internal/docker_network_connectivity_debugger_capture"\n'
            ")\n\nfunc main() {\n"
            f"{body}\n"
            "}\n"
        )
    else:
        body = (
            f'\t_, stats, err := capture.Decode("{escaped}")\n'
            "\tif err != nil {\n"
            '\t\tfmt.Println("ERR:", err.Error())\n'
            "\t\treturn\n"
            "\t}\n"
            "\tb, _ := json.Marshal(stats)\n"
            "\tfmt.Println(string(b))"
        )
        source = (
            "package main\n\nimport (\n"
            '\t"encoding/json"\n'
            '\t"fmt"\n'
            '\tcapture "docker-network-connectivity-debugger/internal/docker_network_connectivity_debugger_capture"\n'
            ")\n\nfunc main() {\n"
            f"{body}\n"
            "}\n"
        )
    (probe_dir / "main.go").write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PATH"] = "/usr/local/go/bin:" + env.get("PATH", "")
    try:
        result = subprocess.run(
            ["go", "run", "./cmd/decodeprobe"],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
    return (result.stdout + result.stderr).strip()


def _run_make(target: str, log_name: str) -> None:
    VERIFIER_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(["make", target], cwd=APP_DIR, capture_output=True, text=True)
    (VERIFIER_DIR / log_name).write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        pytest.fail(f"make {target} failed; see /logs/verifier/{log_name}")


@pytest.fixture(scope="session", autouse=True)
def _verifier_preflight() -> None:
    VERIFIER_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.unlink(missing_ok=True)
    _run_make("build", "build.log")
    _run_make("run", "run.log")
    if not REPORT_PATH.is_file():
        pytest.fail("docker_network_connectivity_debugger_report.json missing after make run")
    shutil.copy(REPORT_PATH, REPORT_FIRST)
    _run_make("run", "run2.log")
    if REPORT_PATH.read_bytes() != REPORT_FIRST.read_bytes():
        pytest.fail("make run not byte-identical across consecutive invocations")


def _scenario_row(report: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for row in report["scenarios"]:
        if row["scenario_id"] == scenario_id:
            return row
    raise KeyError(scenario_id)


def _finding_tuples(row: dict[str, Any]) -> list[tuple[str, str, str, str, int]]:
    return [
        (f["kind"], f["entity_id"], f["detail"], f["operation"], f["event_seq"])
        for f in row["findings"]
    ]


def _max_event_seq(scenario_id: str) -> int:
    _, events = decode_capture(DATA_DIR / scenario_id / CAPTURE_NAME)
    return max((ev["seq"] for ev in events), default=0)


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    assert REPORT_PATH.is_file(), f"missing {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _reference_report() -> dict[str, Any]:
    manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return build_reference_report(DATA_DIR, manifest_data, decode_capture)



def test_report_golden_sha256_byte_identical_digest() -> None:
    """Report bytes must match the golden SHA256 digest for all thirty six bundled scenarios."""
    raw = REPORT_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GOLDEN_REPORT_SHA256
    assert raw == raw.rstrip(b" \t\r\n") + b"\n"
    assert b"  " not in raw


def test_report_matches_independent_python_reference_replay(report: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Every scenario row must match an independent Python reference replay of CNX1 plus rules."""
    expected = _reference_report()
    assert [r["scenario_id"] for r in report["scenarios"]] == manifest["scenarios"]
    assert report == expected


def test_go_capture_decoder_stats_match_report_all_scenarios(report: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Go capture.Decode stats must match report capture counters for every scenario."""
    cap_keys = (
        "format_version",
        "records_total",
        "records_valid",
        "records_rejected",
        "dup_seq_rejects",
        "truncated_tail",
        "payload_bytes",
    )
    for sid in manifest["scenarios"]:
        cap_path = str(DATA_DIR / sid / CAPTURE_NAME)
        out = _go_capture_probe(cap_path, "stats")
        assert not out.startswith("ERR:"), out
        stats = json.loads(out.splitlines()[-1])
        row_cap = _scenario_row(report, sid)["capture"]
        for key in cap_keys:
            assert row_cap[key] == stats[key], f"{sid} capture.{key}"


def test_capture_decode_permission_denied_outside_app_data() -> None:
    """Go decoder must reject capture paths outside /app/data."""
    msg = _go_capture_probe("/app/build/x.cnx", "err")
    assert "permission denied" in msg.lower()


def test_post_replay_audit_event_seq_max_plus_one(report: dict[str, Any]) -> None:
    """Post-replay audit findings must use max decoded event seq plus one per scenario."""
    for row in report["scenarios"]:
        sid = row["scenario_id"]
        audit_seq = _max_event_seq(sid) + 1
        for finding in row["findings"]:
            if finding["kind"] in AUDIT_KINDS:
                assert finding["event_seq"] == audit_seq, f"{sid} {finding['kind']}"


def test_scenario_14_sort_key_duplicate_event_and_zone_blocked_before_duplicate_egress(report: dict[str, Any]) -> None:
    """scenario_14 exercises sort_key on CONNECT_PROBE, duplicate event_id skip, and probe ordering."""
    sid = "docker_network_connectivity_debugger_scenario_14"
    row = _scenario_row(report, sid)
    assert row["duplicate_events_skipped"] == 1
    kinds = [f["kind"] for f in row["findings"]]
    assert kinds.index("ZONE_BLOCKED") < kinds.index("DUPLICATE_EGRESS")
    assert _finding_tuples(row) == [
        ("ZONE_BLOCKED", "api-edge", "billing-svc", "TCP", 8),
        ("DUPLICATE_EGRESS", "billing-svc", "api-edge", "", 8),
    ]


def test_scenario_02_egress_denied_then_bridge_gap_audit(report: dict[str, Any]) -> None:
    """scenario_02 must emit EGRESS_DENIED on the probe then BRIDGE_GAP at audit seq."""
    sid = "docker_network_connectivity_debugger_scenario_02"
    row = _scenario_row(report, sid)
    assert _finding_tuples(row) == [
        ("EGRESS_DENIED", "billing-svc", "api-edge", "TCP", 7),
        ("BRIDGE_GAP", "billing-svc", "api-edge", "", 8),
    ]
    assert row["egress_rules"] == []


def test_scenario_03_network_partition_without_shared_network(report: dict[str, Any]) -> None:
    """scenario_03 containers on different bridge networks must yield NETWORK_PARTITION not egress or zone findings."""
    sid = "docker_network_connectivity_debugger_scenario_03"
    row = _scenario_row(report, sid)
    assert _finding_tuples(row) == [
        ("NETWORK_PARTITION", "billing-svc", "api-edge", "TCP", 9),
    ]


def test_scenario_29_register_dns_alias_overrides_join_alias_valid_probe(report: dict[str, Any]) -> None:
    """scenario_29 REGISTER_DNS payments alias must win over JOIN billing alias for dns resolution."""
    sid = "docker_network_connectivity_debugger_scenario_29"
    row = _scenario_row(report, sid)
    assert row["status"] == "VALID"
    assert row["findings"] == []


def test_scenario_30_duplicate_egress_same_seq_before_zone_blocked_probe(report: dict[str, Any]) -> None:
    """scenario_30 same seq duplicate ALLOW_EGRESS must replay before CONNECT_PROBE at seq 8."""
    sid = "docker_network_connectivity_debugger_scenario_30"
    row = _scenario_row(report, sid)
    assert _finding_tuples(row) == [
        ("ZONE_BLOCKED", "api-edge", "billing-svc", "TCP", 8),
        ("DUPLICATE_EGRESS", "billing-svc", "api-edge", "", 8),
    ]


def test_scenario_31_dual_bridge_networks_emit_single_bridge_gap(report: dict[str, Any]) -> None:
    """scenario_31 two bridge networks with same edge internal pair must dedupe to one BRIDGE_GAP audit."""
    sid = "docker_network_connectivity_debugger_scenario_31"
    row = _scenario_row(report, sid)
    audit_seq = _max_event_seq(sid) + 1
    assert _finding_tuples(row) == [
        ("BRIDGE_GAP", "billing-svc", "api-edge", "", audit_seq),
    ]
    assert len(row["findings"]) == 1


def test_scenario_32_port_unpublished_wrong_probe_port(report: dict[str, Any]) -> None:
    """scenario_32 CONNECT_PROBE to unpublished port must yield PORT_UNPUBLISHED before egress checks."""
    sid = "docker_network_connectivity_debugger_scenario_32"
    row = _scenario_row(report, sid)
    assert _finding_tuples(row) == [
        ("PORT_UNPUBLISHED", "billing-svc", "9090/tcp", "TCP", 8),
    ]


def test_scenario_17_overlay_asymmetry_audit_when_no_internal_to_edge_egress(report: dict[str, Any]) -> None:
    """scenario_17 overlay with edge and internal but no internal to edge egress must emit OVERLAY_ASYMMETRY."""
    sid = "docker_network_connectivity_debugger_scenario_17"
    row = _scenario_row(report, sid)
    audit_seq = _max_event_seq(sid) + 1
    assert _finding_tuples(row) == [
        ("OVERLAY_ASYMMETRY", "billing-svc", "api-edge", "", audit_seq),
    ]


def test_scenario_19_dmz_open_path_and_inspect_unbound_audits(report: dict[str, Any]) -> None:
    """scenario_19 dmz with published port and edge inbound must emit both dmz audit kinds at audit seq."""
    sid = "docker_network_connectivity_debugger_scenario_19"
    row = _scenario_row(report, sid)
    audit_seq = _max_event_seq(sid) + 1
    assert _finding_tuples(row) == [
        ("OPEN_DMZ_PATH", "public-gw", "443/tcp", "", audit_seq),
        ("INSPECT_UNBOUND", "public-gw", "", "", audit_seq),
    ]


def test_scenario_33_policy_override_allows_edge_to_internal_valid_probe(report: dict[str, Any]) -> None:
    """scenario_33 block_edge_to_internal false via policy_overrides must allow edge probe to internal target."""
    sid = "docker_network_connectivity_debugger_scenario_33"
    row = _scenario_row(report, sid)
    assert row["status"] == "VALID"
    assert row["findings"] == []


def test_scenario_34_tls_required_when_net_tls_label_and_no_use_tls(report: dict[str, Any]) -> None:
    """scenario_34 internal target with net tls label and use_tls false must yield TLS_REQUIRED."""
    sid = "docker_network_connectivity_debugger_scenario_34"
    row = _scenario_row(report, sid)
    assert _finding_tuples(row) == [
        ("TLS_REQUIRED", "billing-svc", "", "TCP", 9),
    ]


def test_scenario_35_duplicate_container_registration(report: dict[str, Any]) -> None:
    """scenario_35 second REGISTER_CONTAINER for same container_id must emit DUPLICATE_CONTAINER."""
    sid = "docker_network_connectivity_debugger_scenario_35"
    row = _scenario_row(report, sid)
    assert _finding_tuples(row) == [
        ("DUPLICATE_CONTAINER", "api-edge", "", "", 2),
    ]


def test_scenario_36_connect_probe_unknown_target_empty_operation(report: dict[str, Any]) -> None:
    """scenario_36 CONNECT_PROBE with missing target must use empty operation on UNKNOWN_CONTAINER."""
    sid = "docker_network_connectivity_debugger_scenario_36"
    row = _scenario_row(report, sid)
    assert _finding_tuples(row) == [
        ("UNKNOWN_CONTAINER", "missing-svc", "CONNECT_PROBE", "", 2),
    ]


def test_scenario_25_skipped_duplicate_event_id_increments_audit_seq(report: dict[str, Any]) -> None:
    """scenario_25 skipped duplicate event_id at seq 11 must push BRIDGE_GAP audit to seq 12."""
    sid = "docker_network_connectivity_debugger_scenario_25"
    row = _scenario_row(report, sid)
    assert row["duplicate_events_skipped"] == 1
    assert _finding_tuples(row) == [
        ("EGRESS_DENIED", "billing-svc", "api-edge", "TCP", 7),
        ("BRIDGE_GAP", "billing-svc", "api-edge", "", 12),
    ]


def test_scenario_20_truncated_tail_capture_stats(report: dict[str, Any]) -> None:
    """scenario_20 capture must record truncated_tail without counting a spurious records_total."""
    sid = "docker_network_connectivity_debugger_scenario_20"
    row = _scenario_row(report, sid)
    cap = row["capture"]
    assert cap["truncated_tail"] == 1
    assert cap["records_rejected"] == 1
    assert cap["records_valid"] == 8
    py_stats, _ = decode_capture(DATA_DIR / sid / CAPTURE_NAME)
    assert row["capture"] == py_stats


def test_scenario_05_dup_seq_rejects_capture_counter(report: dict[str, Any]) -> None:
    """scenario_05 must increment dup_seq_rejects when duplicate record seq is rejected."""
    sid = "docker_network_connectivity_debugger_scenario_05"
    row = _scenario_row(report, sid)
    assert row["capture"]["dup_seq_rejects"] == 1
    assert row["capture"]["records_valid"] == 8
    assert row["findings"][0]["kind"] == "ZONE_BLOCKED"


def test_scenario_26_leave_network_clears_dns_alias(report: dict[str, Any]) -> None:
    """scenario_26 LEAVE_NETWORK must clear join alias so dns probe fails."""
    sid = "docker_network_connectivity_debugger_scenario_26"
    row = _scenario_row(report, sid)
    assert _finding_tuples(row) == [
        ("DNS_UNRESOLVED", "api-edge", "payments", "TCP", 9),
    ]


def test_scenario_28_tls_policy_override_allows_probe_without_use_tls(report: dict[str, Any]) -> None:
    """scenario_28 require_tls_on_internal false via policy_overrides must allow non TLS probe."""
    sid = "docker_network_connectivity_debugger_scenario_28"
    row = _scenario_row(report, sid)
    assert row["status"] == "VALID"
    assert row["findings"] == []


def test_scenario_07_zone_blocked_when_egress_present_not_egress_denied(report: dict[str, Any]) -> None:
    """scenario_07 must emit ZONE_BLOCKED not EGRESS_DENIED when egress exists but edge to internal is blocked."""
    sid = "docker_network_connectivity_debugger_scenario_07"
    row = _scenario_row(report, sid)
    assert _finding_tuples(row) == [
        ("ZONE_BLOCKED", "api-edge", "billing-svc", "TCP", 8),
    ]


def test_scenario_21_revoke_egress_then_egress_denied_and_bridge_gap(report: dict[str, Any]) -> None:
    """scenario_21 REVOKE_EGRESS must remove edge so probe yields EGRESS_DENIED then BRIDGE_GAP audit."""
    sid = "docker_network_connectivity_debugger_scenario_21"
    row = _scenario_row(report, sid)
    audit_seq = _max_event_seq(sid) + 1
    assert _finding_tuples(row) == [
        ("EGRESS_DENIED", "billing-svc", "api-edge", "TCP", 9),
        ("BRIDGE_GAP", "billing-svc", "api-edge", "", audit_seq),
    ]
    assert row["egress_rules"] == []


def test_build_directory_contains_only_binary_and_report() -> None:
    """build output directory must contain only the debugger binary and JSON report."""
    names = sorted(p.name for p in (APP_DIR / "build").iterdir())
    assert names == ["docker-network-connectivity-debugger", "docker_network_connectivity_debugger_report.json"]
    assert BINARY.is_file() and not BINARY.is_symlink()
    assert REPORT_PATH.is_file() and not REPORT_PATH.is_symlink()
