#!/usr/bin/env python3
"""Generate bundled CNX1 captures and scenario JSON for docker network connectivity debugger fixtures."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

DATA = Path(__file__).resolve().parent / "docker_network_connectivity_debugger_data"


def encode_cnx(events: list[dict], *, dup_record: int | None = None, truncate: bool = False) -> bytes:
    out = bytearray(b"CNX1")
    out += struct.pack("<I", 1)
    record_seq = 1
    for ev in events:
        payload = json.dumps(ev, separators=(",", ":")).encode("utf-8")
        plen = len(payload)
        hdr = struct.pack("<I H H I", record_seq, 0, 0, plen)
        checksum = zlib.crc32(hdr + payload) & 0xFFFFFFFF
        out += hdr + payload + struct.pack("<I", checksum)
        if dup_record is not None and record_seq == dup_record:
            out += hdr + payload + struct.pack("<I", checksum)
        record_seq += 1
    if truncate:
        out += b"\x01\x02\x03"
    return bytes(out)


def e(seq: int, kind: str, event_id: str, container_id: str = "", **kw: object) -> dict:
    row: dict = {"seq": seq, "event_id": event_id, "container_id": container_id, "kind": kind}
    row.update(kw)
    return row


SCENARIOS: list[tuple[dict, list[dict], dict]] = [
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_01"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "cache-svc", zone="internal"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "cache-svc", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "BIND_LABEL", "b1", "billing-svc", label="net:inspect"),
            e(8, "ALLOW_EGRESS", "g1", "billing-svc", from_container="cache-svc", to_container="billing-svc"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="cache-svc", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_02"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_03"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="net-a", driver="bridge"),
            e(4, "CREATE_NETWORK", "n2", "", network_id="net-b", driver="bridge"),
            e(5, "JOIN_NETWORK", "j1", "api-edge", network_id="net-a"),
            e(6, "JOIN_NETWORK", "j2", "billing-svc", network_id="net-b"),
            e(7, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(8, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_04"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(7, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=9090, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_05"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {"dup_record": 3},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_06"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "REGISTER_DNS", "d1", "billing-svc", network_id="mesh-bridge", alias="billing"),
            e(7, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(8, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", dns_alias="payments", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_07"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_08"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "cache-svc", zone="internal"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "cache-svc", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "BIND_LABEL", "b1", "billing-svc", label="net:tls"),
            e(8, "ALLOW_EGRESS", "g1", "billing-svc", from_container="cache-svc", to_container="billing-svc"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="cache-svc", target_id="billing-svc", port=8080, protocol="tcp", use_tls=False),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_09"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "CONNECT_PROBE", "c1", "api-edge", source_id="api-edge", target_id="ghost-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_10"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "JOIN_NETWORK", "j1", "api-edge", network_id="missing-net"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_11"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "api-edge", zone="edge"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_12"},
        [
            e(1, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(2, "CREATE_NETWORK", "n2", "", network_id="mesh-bridge", driver="bridge"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_13"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(3, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(4, "JOIN_NETWORK", "j2", "api-edge", network_id="mesh-bridge"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_14"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "ALLOW_EGRESS", "g2", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {
            "scenario_id": "docker_network_connectivity_debugger_scenario_15",
            "policy_overrides": {"block_edge_to_internal": False},
        },
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_16"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_17"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-overlay", driver="overlay"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-overlay"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-overlay"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_18"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "public-gw", zone="dmz"),
            e(2, "PUBLISH_PORT", "p1", "public-gw", port=443, protocol="tcp"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_19"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "public-gw", zone="dmz"),
            e(3, "PUBLISH_PORT", "p1", "public-gw", port=443, protocol="tcp"),
            e(4, "ALLOW_EGRESS", "g1", "public-gw", from_container="api-edge", to_container="public-gw"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_20"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {"truncate": True},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_21"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "REVOKE_EGRESS", "x1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_22"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="net-a", driver="bridge"),
            e(4, "CREATE_NETWORK", "n2", "", network_id="net-b", driver="bridge"),
            e(5, "JOIN_NETWORK", "j1", "api-edge", network_id="net-a"),
            e(6, "JOIN_NETWORK", "j2", "billing-svc", network_id="net-b"),
            e(7, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(8, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(9, "LEAVE_NETWORK", "l1", "api-edge", network_id="net-a"),
            e(10, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_23", "require_shared_network": False},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="net-a", driver="bridge"),
            e(4, "CREATE_NETWORK", "n2", "", network_id="net-b", driver="bridge"),
            e(5, "JOIN_NETWORK", "j1", "api-edge", network_id="net-a"),
            e(6, "JOIN_NETWORK", "j2", "billing-svc", network_id="net-b"),
            e(7, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(8, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_24"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "cache-svc", zone="internal"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "cache-svc", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge", alias="payments"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="cache-svc", to_container="billing-svc"),
            e(8, "CONNECT_PROBE", "c1", "billing-svc", source_id="cache-svc", target_id="billing-svc", port=8080, protocol="tcp", dns_alias="payments", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_25"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
            e(11, "BIND_LABEL", "z1", "billing-svc", label="tag-a"),
            e(11, "BIND_LABEL", "z1", "billing-svc", label="tag-b"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_26"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge", alias="payments"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "LEAVE_NETWORK", "l1", "billing-svc", network_id="mesh-bridge"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", dns_alias="payments", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_27"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-overlay", driver="overlay"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-overlay"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-overlay"),
            e(6, "ALLOW_EGRESS", "g1", "billing-svc", from_container="billing-svc", to_container="api-edge"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_28", "policy_overrides": {"require_tls_on_internal": False}},
        [
            e(1, "REGISTER_CONTAINER", "r1", "cache-svc", zone="internal"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "cache-svc", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "BIND_LABEL", "b1", "billing-svc", label="net:tls"),
            e(8, "ALLOW_EGRESS", "g1", "billing-svc", from_container="cache-svc", to_container="billing-svc"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="cache-svc", target_id="billing-svc", port=8080, protocol="tcp", use_tls=False),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_29"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "cache-svc", zone="internal"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "cache-svc", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge", alias="billing"),
            e(6, "REGISTER_DNS", "d1", "billing-svc", network_id="mesh-bridge", alias="payments"),
            e(7, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(8, "ALLOW_EGRESS", "g1", "billing-svc", from_container="cache-svc", to_container="billing-svc"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="cache-svc", target_id="billing-svc", port=8080, protocol="tcp", dns_alias="payments", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_30"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "ALLOW_EGRESS", "g2", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_31"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="bridge-a", driver="bridge"),
            e(4, "CREATE_NETWORK", "n2", "", network_id="bridge-b", driver="bridge"),
            e(5, "JOIN_NETWORK", "j1", "api-edge", network_id="bridge-a"),
            e(6, "JOIN_NETWORK", "j2", "billing-svc", network_id="bridge-a"),
            e(7, "JOIN_NETWORK", "j3", "api-edge", network_id="bridge-b"),
            e(8, "JOIN_NETWORK", "j4", "billing-svc", network_id="bridge-b"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_32"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=9090, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_33", "policy_overrides": {"block_edge_to_internal": False}},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "api-edge", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "ALLOW_EGRESS", "g1", "billing-svc", from_container="api-edge", to_container="billing-svc"),
            e(8, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="billing-svc", port=8080, protocol="tcp", use_tls=True),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_34"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "cache-svc", zone="internal"),
            e(2, "REGISTER_CONTAINER", "r2", "billing-svc", zone="internal"),
            e(3, "CREATE_NETWORK", "n1", "", network_id="mesh-bridge", driver="bridge"),
            e(4, "JOIN_NETWORK", "j1", "cache-svc", network_id="mesh-bridge"),
            e(5, "JOIN_NETWORK", "j2", "billing-svc", network_id="mesh-bridge"),
            e(6, "PUBLISH_PORT", "p1", "billing-svc", port=8080, protocol="tcp"),
            e(7, "BIND_LABEL", "b1", "billing-svc", label="net:tls"),
            e(8, "ALLOW_EGRESS", "g1", "billing-svc", from_container="cache-svc", to_container="billing-svc"),
            e(9, "CONNECT_PROBE", "c1", "billing-svc", source_id="cache-svc", target_id="billing-svc", port=8080, protocol="tcp", use_tls=False),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_35"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "REGISTER_CONTAINER", "r2", "api-edge", zone="dmz"),
        ],
        {},
    ),
    (
        {"scenario_id": "docker_network_connectivity_debugger_scenario_36"},
        [
            e(1, "REGISTER_CONTAINER", "r1", "api-edge", zone="edge"),
            e(2, "CONNECT_PROBE", "c1", "billing-svc", source_id="api-edge", target_id="missing-svc", port=8080, protocol="tcp", use_tls=False),
        ],
        {},
    ),
]


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    manifest = {"scenarios": [cfg["scenario_id"] for cfg, _, _ in SCENARIOS]}
    (DATA / "docker_network_connectivity_debugger_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    for cfg, events, opts in SCENARIOS:
        sid = cfg["scenario_id"]
        (DATA / f"{sid}.json").write_text(
            json.dumps(cfg, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        cap_dir = DATA / sid
        cap_dir.mkdir(parents=True, exist_ok=True)
        blob = encode_cnx(
            events,
            dup_record=opts.get("dup_record"),
            truncate=bool(opts.get("truncate")),
        )
        (cap_dir / "docker_network_connectivity_debugger_capture.cnx").write_bytes(blob)


if __name__ == "__main__":
    main()
