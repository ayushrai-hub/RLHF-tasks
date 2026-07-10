import json
import os
import shutil
import subprocess
from datetime import datetime
from datetime import timedelta
from pathlib import Path


WORKSPACE = Path("/workspace")
PUBLIC_CONFIG = WORKSPACE / "task_file" / "config.json"
PUBLIC_EVENTS = WORKSPACE / "task_file" / "events.jsonl"
SOLUTION = WORKSPACE / "log_reconciler.go"

REASON_ORDER = [
    "invalid_schema",
    "unknown_kind",
    "unknown_service",
    "trace_not_active",
    "trace_already_active",
    "service_mismatch",
    "route_not_allowed",
    "capacity_full",
    "loop_blocked",
    "target_missing",
    "target_not_voidable",
    "target_trace_mismatch",
    "target_already_voided",
    "void_too_late",
]


def load_jsonl(path):
    records = []
    for line_no, line in enumerate(path.read_text().splitlines(), start=1):
        record = json.loads(line)
        record["_line"] = line_no
        records.append(record)
    return records


def write_case(tmp_path, config, events):
    config_path = tmp_path / "config.json"
    events_path = tmp_path / "events.jsonl"
    out_path = tmp_path / "out" / "report.json"
    config_path.write_text(json.dumps(config, sort_keys=True))
    rows = []
    for event in events:
        clean = {key: value for key, value in event.items() if not key.startswith("_")}
        rows.append(json.dumps(clean, separators=(",", ":")))
    events_path.write_text("\n".join(rows) + "\n")
    return config_path, events_path, out_path


def parse_time(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None


def canonical_key(record):
    parsed = parse_time(record.get("ts"))
    if parsed is None:
        parsed = datetime.max.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return (
        parsed.isoformat(),
        str(record.get("node", "")),
        record.get("seq") if isinstance(record.get("seq"), int) else 10**12,
        record["_line"],
    )


def schema_invalid(record):
    required = {
        "event_id": str,
        "ts": str,
        "node": str,
        "seq": int,
        "trace": str,
        "kind": str,
        "flags": list,
    }
    for key, typ in required.items():
        if not isinstance(record.get(key), typ):
            return True
    if parse_time(record.get("ts")) is None:
        return True
    if not all(isinstance(flag, str) for flag in record.get("flags", [])):
        return True
    nullable_strings = ["service", "next_service", "target", "req"]
    for key in nullable_strings:
        if record.get(key) is not None and not isinstance(record.get(key), str):
            return True
    for key in ["bytes", "status"]:
        if record.get(key) is not None and not isinstance(record.get(key), int):
            return True
    return isinstance(record.get("bytes"), int) and record["bytes"] < 0


def ordered_reasons(reasons):
    return [reason for reason in REASON_ORDER if reason in reasons]


def reconcile(config, records):
    routes = config["routes"]
    capacities = config["capacities"]
    billable_statuses = set(config["billable_statuses"])
    cap = config["trace_byte_cap"]
    grace = timedelta(milliseconds=config["void_grace_ms"])
    active_counts = {service: 0 for service in capacities}
    peaks = {service: 0 for service in capacities}
    active = {}
    requests = {}
    accepted_events = {}
    bytes_events = {}
    voided_targets = set()
    adjustments = []
    audit = []
    seen_positions = set()
    accepted = 0
    rejected = 0
    ignored = 0

    for record in sorted(records, key=canonical_key):
        position = (record.get("node"), record.get("seq"))
        event_id = record.get("event_id")
        if position in seen_positions:
            ignored += 1
            audit.append(
                {
                    "event_id": event_id,
                    "line": record["_line"],
                    "action": "ignored",
                    "reasons": ["duplicate_position"],
                }
            )
            continue
        seen_positions.add(position)

        if schema_invalid(record):
            rejected += 1
            audit.append(
                {
                    "event_id": event_id,
                    "line": record["_line"],
                    "action": "rejected",
                    "reasons": ["invalid_schema"],
                }
            )
            continue

        kind = record["kind"]
        trace = record["trace"]
        service = record.get("service")
        next_service = record.get("next_service")
        reasons = set()
        known_service = service is None or service in capacities
        if kind not in {"start", "hop", "bytes", "end", "void"}:
            reasons.add("unknown_kind")
        if kind in {"start", "bytes", "end"} and service not in capacities:
            reasons.add("unknown_service")
            known_service = False
        if kind == "hop":
            if service not in capacities or next_service not in capacities:
                reasons.add("unknown_service")
                known_service = False

        if kind == "start" and known_service:
            if trace in active:
                reasons.add("trace_already_active")
            if service in capacities and active_counts[service] >= capacities[service]:
                reasons.add("capacity_full")
        elif kind in {"hop", "bytes", "end"} and kind in {"hop", "bytes", "end"}:
            current = active.get(trace)
            if current is None:
                reasons.add("trace_not_active")
            elif service != current["final_service"]:
                reasons.add("service_mismatch")
            if kind == "hop" and current is not None and known_service:
                allowed = next_service in routes.get(service, [])
                if not allowed:
                    reasons.add("route_not_allowed")
                loop = next_service in current["path"]
                if loop and "loop_ok" not in record["flags"]:
                    reasons.add("loop_blocked")
                if allowed and not loop and active_counts[next_service] >= capacities[next_service]:
                    reasons.add("capacity_full")
                if allowed and loop and "loop_ok" in record["flags"]:
                    same_service = service == next_service
                    remaining = active_counts[next_service] - (1 if same_service else 0)
                    if remaining >= capacities[next_service]:
                        reasons.add("capacity_full")
        elif kind == "void":
            target = accepted_events.get(record.get("target"))
            if target is None:
                reasons.add("target_missing")
            else:
                if target["kind"] != "bytes":
                    reasons.add("target_not_voidable")
                if target["trace"] != trace:
                    reasons.add("target_trace_mismatch")
                if target["event_id"] in voided_targets:
                    reasons.add("target_already_voided")
                if parse_time(record["ts"]) - parse_time(target["ts"]) > grace:
                    reasons.add("void_too_late")

        if reasons:
            rejected += 1
            audit.append(
                {
                    "event_id": event_id,
                    "line": record["_line"],
                    "action": "rejected",
                    "reasons": ordered_reasons(reasons),
                }
            )
            continue

        accepted += 1
        audit.append(
            {
                "event_id": event_id,
                "line": record["_line"],
                "action": "accepted",
                "reasons": [],
            }
        )
        accepted_events[event_id] = record

        if kind == "start":
            request = {
                "trace": trace,
                "req": record["req"],
                "opened_at": record["ts"],
                "closed_at": None,
                "status": "open",
                "status_code": None,
                "final_service": service,
                "path": [service],
                "raw_bytes": 0,
                "billable_bytes": 0,
                "warnings": [],
                "_start_event": event_id,
                "_end_event": None,
            }
            requests[trace] = request
            active[trace] = request
            active_counts[service] += 1
            peaks[service] = max(peaks[service], active_counts[service])
        elif kind == "hop":
            request = active[trace]
            old_service = request["final_service"]
            if next_service in request["path"] and "loop_allowed" not in request["warnings"]:
                request["warnings"].append("loop_allowed")
            active_counts[old_service] -= 1
            active_counts[next_service] += 1
            peaks[next_service] = max(peaks[next_service], active_counts[next_service])
            request["final_service"] = next_service
            request["path"].append(next_service)
        elif kind == "bytes":
            contribution = record["bytes"] // 2 if "sampled" in record["flags"] else record["bytes"]
            request = active[trace]
            request["raw_bytes"] += contribution
            if "sampled" in record["flags"] and "sampled_bytes" not in request["warnings"]:
                request["warnings"].append("sampled_bytes")
            bytes_events[event_id] = contribution
        elif kind == "end":
            request = active.pop(trace)
            request["closed_at"] = record["ts"]
            request["status"] = "closed"
            request["status_code"] = record["status"]
            request["_end_event"] = event_id
            active_counts[service] -= 1
        elif kind == "void":
            target_id = record["target"]
            target = accepted_events[target_id]
            contribution = bytes_events[target_id]
            voided_targets.add(target_id)
            requests[target["trace"]]["raw_bytes"] -= contribution
            adjustments.append(
                {
                    "trace": target["trace"],
                    "kind": "void",
                    "amount": -contribution,
                    "event_id": event_id,
                    "source_event": target_id,
                }
            )

    for request in requests.values():
        request["warnings"] = sorted(request["warnings"])
        if request["status"] == "closed" and request["status_code"] in billable_statuses:
            request["billable_bytes"] = min(request["raw_bytes"], cap)
        else:
            request["billable_bytes"] = 0
        if request["raw_bytes"] != request["billable_bytes"]:
            kind = "cap"
            if request["status"] != "closed" or request["status_code"] not in billable_statuses:
                kind = "nonbillable"
            adjustments.append(
                {
                    "trace": request["trace"],
                    "kind": kind,
                    "amount": request["billable_bytes"] - request["raw_bytes"],
                    "event_id": request["_end_event"],
                    "source_event": request["_start_event"],
                }
            )

    public_requests = []
    for request in sorted(requests.values(), key=lambda item: item["trace"]):
        public_requests.append(
            {
                key: request[key]
                for key in [
                    "trace",
                    "req",
                    "opened_at",
                    "closed_at",
                    "status",
                    "status_code",
                    "final_service",
                    "path",
                    "raw_bytes",
                    "billable_bytes",
                    "warnings",
                ]
            }
        )

    adjustments.sort(
        key=lambda item: (
            item["trace"],
            item["kind"],
            "" if item["source_event"] is None else item["source_event"],
            "" if item["event_id"] is None else item["event_id"],
        )
    )
    peaks_list = [
        {"service": service, "peak": peaks[service]}
        for service in sorted(peaks)
    ]
    return {
        "requests": public_requests,
        "audit": audit,
        "adjustments": adjustments,
        "peaks": peaks_list,
        "summary": {
            "processed": len(records),
            "accepted": accepted,
            "rejected": rejected,
            "ignored": ignored,
            "open_requests": sum(1 for item in requests.values() if item["status"] == "open"),
            "closed_requests": sum(1 for item in requests.values() if item["status"] == "closed"),
            "billable_total": sum(item["billable_bytes"] for item in requests.values()),
        },
    }


def run_solver(tmp_path, config, events):
    assert SOLUTION.exists(), "missing /workspace/log_reconciler.go"
    config_path, events_path, out_path = write_case(tmp_path, config, events)
    result = subprocess.run(
        [
            "go",
            "run",
            str(SOLUTION),
            str(config_path),
            str(events_path),
            str(out_path),
        ],
        cwd=WORKSPACE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert out_path.exists(), "solver did not create the requested output path"
    with out_path.open() as handle:
        return json.load(handle)


def base_config():
    return json.loads(PUBLIC_CONFIG.read_text())


def event(event_id, offset_ms, node, seq, trace, kind, service=None, **kwargs):
    base = datetime.fromisoformat("2026-05-01T12:00:00+00:00")
    ts = (base + timedelta(milliseconds=offset_ms)).isoformat(timespec="milliseconds")
    return {
        "event_id": event_id,
        "ts": ts.replace("+00:00", "Z"),
        "node": node,
        "seq": seq,
        "trace": trace,
        "kind": kind,
        "service": service,
        "next_service": kwargs.get("next_service"),
        "bytes": kwargs.get("bytes"),
        "status": kwargs.get("status"),
        "target": kwargs.get("target"),
        "flags": kwargs.get("flags", []),
        "req": kwargs.get("req"),
    }


def numbered(events):
    return [dict(item, _line=index) for index, item in enumerate(events, start=1)]


def variant_capacity_loop_and_cap():
    config = base_config()
    config["capacities"]["cache"] = 2
    events = [
        event("a1", 0, "ship-a", 1, "A", "start", "edge", req="GET /a"),
        event("b1", 5, "ship-b", 1, "B", "start", "edge", req="GET /b"),
        event("a2", 10, "ship-a", 2, "A", "hop", "edge", next_service="cache"),
        event("b2", 15, "ship-b", 2, "B", "hop", "edge", next_service="cache"),
        event("a3", 20, "ship-a", 3, "A", "hop", "cache", next_service="edge", flags=["loop_ok"]),
        event("a4", 21, "ship-a", 4, "A", "hop", "edge", next_service="cache"),
        event("a5", 22, "ship-a", 5, "A", "bytes", "cache", bytes=2000),
        event("a6", 23, "ship-a", 6, "A", "end", "cache", status=200),
        event("b3", 24, "ship-b", 3, "B", "bytes", "cache", bytes=99, flags=["sampled"]),
        event("b4", 25, "ship-b", 4, "B", "end", "cache", status=204),
    ]
    return config, numbered(events)


def variant_void_rejections_and_duplicates():
    config = base_config()
    events = [
        event("x1", 0, "ship-a", 1, "X", "start", "edge", req="GET /x"),
        event("x2", 1, "ship-a", 2, "X", "bytes", "edge", bytes=101),
        event("x3", 2, "ship-a", 3, "X", "void", target="x2"),
        event("x4", 3, "ship-a", 4, "Y", "void", target="x2"),
        event("x5", 9000, "ship-a", 5, "X", "void", target="x2"),
        event("x6", 4, "ship-b", 4, "X", "void", target="missing"),
        event("x7", 5, "ship-a", 6, "X", "end", "edge", status=200),
        event("x8", 6, "ship-a", 6, "X", "bytes", "edge", bytes=7),
    ]
    return config, numbered(events)


def variant_canonical_order_not_file_order():
    config = base_config()
    events = [
        event("c3", 30, "ship-b", 3, "C", "bytes", "auth", bytes=10),
        event("c1", 10, "ship-b", 1, "C", "start", "edge", req="GET /c"),
        event("c2", 20, "ship-b", 2, "C", "hop", "edge", next_service="auth"),
        event("d1", 15, "ship-a", 9, "D", "start", "edge", req="GET /d"),
        event("d2", 25, "ship-a", 10, "D", "end", "edge", status=500),
        event("c4", 40, "ship-b", 4, "C", "end", "auth", status=201),
    ]
    return config, numbered(events)


def variant_additive_reasons():
    config = base_config()
    events = [
        event("r1", 0, "ship-a", 1, "R", "start", "edge", req="GET /r"),
        event("r2", 1, "ship-a", 2, "R", "hop", "pay", next_service="edge"),
        event("r3", 2, "ship-a", 3, "R", "hop", "edge", next_service="ledger"),
        event("r4", 3, "ship-a", 4, "R", "hop", "edge", next_service="auth"),
        event("r5", 4, "ship-a", 5, "R", "hop", "auth", next_service="edge"),
        event("r6", 5, "ship-a", 6, "R", "bytes", "auth", bytes=80),
        event("r7", 6, "ship-a", 7, "R", "end", "auth", status=200),
    ]
    return config, numbered(events)


def variant_stress_interactions():
    config = base_config()
    config["trace_byte_cap"] = 300
    events = [
        event("s1", 0, "ship-a", 10, "S", "start", "edge", req="POST /s"),
        event("t1", 1, "ship-a", 11, "T", "start", "edge", req="POST /t"),
        event("u1", 2, "ship-b", 10, "U", "start", "edge", req="POST /u"),
        event("s2", 3, "ship-a", 12, "S", "hop", "edge", next_service="auth"),
        event("t2", 4, "ship-a", 13, "T", "hop", "edge", next_service="auth"),
        event("s3", 5, "ship-a", 14, "S", "bytes", "auth", bytes=500, flags=["sampled"]),
        event("s4", 6, "ship-a", 15, "S", "hop", "auth", next_service="cache"),
        event("s5", 7, "ship-a", 16, "S", "hop", "cache", next_service="edge", flags=["loop_ok"]),
        event("s6", 8, "ship-a", 17, "S", "hop", "edge", next_service="cache"),
        event("s7", 9, "ship-a", 18, "S", "bytes", "cache", bytes=200),
        event("s8", 10, "ship-a", 19, "S", "void", target="s3"),
        event("s9", 11, "ship-a", 20, "S", "end", "cache", status=200),
        event("t3", 12, "ship-a", 21, "T", "hop", "edge", next_service="auth"),
        event("t4", 13, "ship-a", 22, "T", "bytes", "auth", bytes=99),
        event("t5", 14, "ship-a", 23, "T", "end", "auth", status=503),
    ]
    return config, numbered(events)


def assert_matches_reference(tmp_path, config, records):
    actual = run_solver(tmp_path, config, records)
    expected = reconcile(config, records)
    assert actual == expected


def test_public_fixture_matches_reference(tmp_path):
    config = base_config()
    records = load_jsonl(PUBLIC_EVENTS)
    assert_matches_reference(tmp_path, config, records)


def test_public_input_files_are_not_modified():
    assert PUBLIC_CONFIG.exists()
    assert PUBLIC_EVENTS.exists()
    assert "trace_byte_cap" in PUBLIC_CONFIG.read_text()
    assert "duplicate_position" not in PUBLIC_EVENTS.read_text()


def test_capacity_loop_and_cap_variant(tmp_path):
    config, records = variant_capacity_loop_and_cap()
    assert_matches_reference(tmp_path, config, records)


def test_void_rejections_and_duplicate_positions(tmp_path):
    config, records = variant_void_rejections_and_duplicates()
    assert_matches_reference(tmp_path, config, records)


def test_canonical_order_not_file_order(tmp_path):
    config, records = variant_canonical_order_not_file_order()
    assert_matches_reference(tmp_path, config, records)


def test_additive_reason_ordering(tmp_path):
    config, records = variant_additive_reasons()
    assert_matches_reference(tmp_path, config, records)


def test_stress_combines_capacity_void_loop_sampling_and_status(tmp_path):
    config, records = variant_stress_interactions()
    assert_matches_reference(tmp_path, config, records)


def test_solver_does_not_depend_on_public_paths_only(tmp_path):
    config, records = variant_canonical_order_not_file_order()
    renamed = tmp_path / "renamed.go"
    shutil.copyfile(SOLUTION, renamed)
    config_path, events_path, out_path = write_case(tmp_path, config, records)
    result = subprocess.run(
        ["go", "run", str(renamed), str(config_path), str(events_path), str(out_path)],
        cwd=WORKSPACE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(out_path.read_text()) == reconcile(config, records)


def test_no_prebaked_report_only_solution(tmp_path):
    stale = WORKSPACE / "out" / "report.json"
    if stale.exists():
        os.remove(stale)
    config, records = variant_stress_interactions()
    assert_matches_reference(tmp_path, config, records)
