import csv
import json
import random
import subprocess
from pathlib import Path


APP_ROOT = Path("/app")
BIN = APP_ROOT / "bin" / "flowgap"
BUILD = APP_ROOT / "scripts" / "build.sh"
FIXTURE = APP_ROOT / "input" / "packets.csv"
HEADER = ["stream_id", "packet_no", "ts", "src", "dst", "seq", "ack", "payload_len", "flags"]
SUMMARY_KEYS = [
    "segments", "directions", "bytes_observed", "in_order", "out_of_order",
    "retransmit", "overlap", "zero_length", "reset", "gaps", "open_gaps",
    "abandoned_gaps",
]
STATUS_KEYS = ["in_order", "out_of_order", "retransmit", "overlap", "zero_length", "reset"]


def setUpModule() -> None:
    subprocess.run([str(BUILD)], check=True)


def run_flowgap(csv_path: Path, out_path: Path, stream: str | None = None) -> dict:
    cmd = [str(BIN), "--csv", str(csv_path), "--out", str(out_path)]
    if stream is not None:
        cmd.extend(["--stream", stream])
    subprocess.run(cmd, check=True)
    raw = out_path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    assert not raw.endswith("\n\n")
    assert ": " not in raw and ", " not in raw
    return json.loads(raw)


def direction_of(row: dict) -> str:
    return f"{row['src']} -> {row['dst']}"


def valid_flags(flags: str, payload_len: int) -> bool:
    if not flags:
        return False
    allowed = set("AFPRS")
    if any(ch not in allowed for ch in flags):
        return False
    if len(set(flags)) != len(flags):
        return False
    if "R" in flags and (payload_len != 0 or flags not in {"R", "AR"}):
        return False
    return True


def consumed_len(row: dict) -> int:
    if "R" in row["flags"]:
        return 0
    return int(row["payload_len"]) + (1 if "S" in row["flags"] else 0) + (1 if "F" in row["flags"] else 0)


def parse_rows(csv_path: Path):
    rows = []
    diagnostics = []
    rows_read = 0
    rows_skipped = 0
    saw_header = False
    seen_packets: set[tuple[str, str, str, int]] = set()
    last_ts: dict[tuple[str, str, str], str] = {}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for file_row, fields in enumerate(reader, start=1):
            if not fields or all(field == "" for field in fields):
                continue
            if not saw_header:
                assert fields == HEADER
                saw_header = True
                continue
            rows_read += 1
            if len(fields) != len(HEADER):
                diagnostics.append({"row": file_row, "error": "wrong column count"})
                rows_skipped += 1
                continue
            item = dict(zip(HEADER, fields))
            if item["stream_id"] == "":
                diagnostics.append({"row": file_row, "error": "blank stream_id"})
                rows_skipped += 1
                continue
            ok = True
            for key in ["packet_no", "seq", "ack", "payload_len"]:
                try:
                    value = int(item[key])
                    if value < 0:
                        raise ValueError
                    item[key] = value
                except ValueError:
                    ok = False
            if not ok:
                diagnostics.append({"row": file_row, "error": "invalid integer"})
                rows_skipped += 1
                continue
            if not valid_flags(item["flags"], item["payload_len"]):
                diagnostics.append({"row": file_row, "error": "invalid flags"})
                rows_skipped += 1
                continue
            direction_key = (item["stream_id"], item["src"], item["dst"])
            packet_key = (*direction_key, item["packet_no"])
            if packet_key in seen_packets:
                diagnostics.append({"row": file_row, "error": "duplicate packet_no"})
                rows_skipped += 1
                continue
            previous_ts = last_ts.get(direction_key)
            if previous_ts is not None and item["ts"] < previous_ts:
                diagnostics.append({"row": file_row, "error": "timestamp regression"})
                rows_skipped += 1
                continue
            seen_packets.add(packet_key)
            last_ts[direction_key] = item["ts"]
            rows.append(item)
    assert saw_header
    return rows, diagnostics, rows_read, rows_skipped


def advance_frontier(expected: int, intervals: list[tuple[int, int]], gaps: list[dict], packet_no: int, direction: str) -> tuple[int, bool]:
    filled = False
    changed = True
    while changed:
        changed = False
        for start, end in intervals:
            if start <= expected < end:
                expected = end
                changed = True
    for gap in gaps:
        if gap["direction"] == direction and gap["status"] == "open" and expected >= gap["end"]:
            gap["status"] = "filled"
            gap["filled_by"] = packet_no
            filled = True
    return expected, filled


def new_state() -> dict:
    return {"expected": 0, "initialized": False, "intervals": [], "seen_gaps": set()}


def classify_stream(stream_id: str, rows: list[dict]) -> dict:
    states: dict[str, dict] = {}
    gaps: list[dict] = []
    segments = []
    counts = {name: 0 for name in STATUS_KEYS}
    bytes_observed = 0

    for row in rows:
        direction = direction_of(row)
        state = states.setdefault(direction, new_state())
        seq = int(row["seq"])
        payload_len = int(row["payload_len"])
        consumed = consumed_len(row)
        end_seq = seq + consumed
        if "R" in row["flags"]:
            expected_before = state["expected"] if state["initialized"] else seq
            status = "reset"
            gap_before = None
            fills_gap = False
            for gap in gaps:
                if gap["direction"] == direction and gap["status"] == "open":
                    gap["status"] = "abandoned"
            states[direction] = new_state()
        elif consumed == 0:
            expected_before = state["expected"] if state["initialized"] else seq
            status = "zero_length"
            gap_before = None
            fills_gap = False
        else:
            if not state["initialized"]:
                state["expected"] = seq
                state["initialized"] = True
            expected_before = state["expected"]
            if end_seq <= state["expected"]:
                status = "retransmit"
                gap_before = None
                fills_gap = False
            elif seq < state["expected"]:
                status = "overlap"
                gap_before = None
                state["intervals"].append((seq, end_seq))
                state["expected"], fills_gap = advance_frontier(
                    state["expected"], state["intervals"], gaps, int(row["packet_no"]), direction
                )
            elif seq == state["expected"]:
                status = "in_order"
                gap_before = None
                state["intervals"].append((seq, end_seq))
                state["expected"], fills_gap = advance_frontier(
                    state["expected"], state["intervals"], gaps, int(row["packet_no"]), direction
                )
            else:
                status = "out_of_order"
                gap_before = {"start": state["expected"], "end": seq, "length": seq - state["expected"]}
                gap_key = (direction, state["expected"], seq)
                if gap_key not in state["seen_gaps"]:
                    gaps.append({
                        "direction": direction,
                        "start": state["expected"],
                        "end": seq,
                        "length": seq - state["expected"],
                        "introduced_by": int(row["packet_no"]),
                        "status": "open",
                        "filled_by": None,
                    })
                    state["seen_gaps"].add(gap_key)
                state["intervals"].append((seq, end_seq))
                fills_gap = False
        counts[status] += 1
        bytes_observed += payload_len
        segments.append({
            "packet_no": int(row["packet_no"]),
            "direction": direction,
            "seq": seq,
            "end_seq": end_seq,
            "payload_len": payload_len,
            "flags": row["flags"],
            "status": status,
            "expected_before": expected_before,
            "gap_before": gap_before,
            "fills_gap": fills_gap,
        })

    summary = {
        "segments": len(segments),
        "directions": len(states),
        "bytes_observed": bytes_observed,
        "in_order": counts["in_order"],
        "out_of_order": counts["out_of_order"],
        "retransmit": counts["retransmit"],
        "overlap": counts["overlap"],
        "zero_length": counts["zero_length"],
        "reset": counts["reset"],
        "gaps": len(gaps),
        "open_gaps": sum(1 for gap in gaps if gap["status"] == "open"),
        "abandoned_gaps": sum(1 for gap in gaps if gap["status"] == "abandoned"),
    }
    return {"stream_id": stream_id, "segments": segments, "gaps": gaps, "summary": summary}


def expected_payload(csv_path: Path, stream: str | None = None) -> dict:
    rows, diagnostics, rows_read, rows_skipped = parse_rows(csv_path)
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        if stream is not None and row["stream_id"] != stream:
            continue
        grouped.setdefault(row["stream_id"], []).append(row)

    streams = [classify_stream(stream_id, grouped[stream_id]) for stream_id in sorted(grouped)]
    totals = {key: 0 for key in ["streams", *SUMMARY_KEYS]}
    totals["streams"] = len(streams)
    for stream_obj in streams:
        for key in SUMMARY_KEYS:
            totals[key] += stream_obj["summary"][key]

    return {
        "input": {
            "csv": str(csv_path),
            "stream_filter": stream,
            "rows_read": rows_read,
            "rows_skipped": rows_skipped,
        },
        "streams": streams,
        "totals": totals,
        "diagnostics": diagnostics,
    }


def write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)


def write_csv_with_leading_blank(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write("\n")
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for row in rows:
            if row == []:
                handle.write("\n")
            else:
                writer.writerow(row)


def hidden_csv(path: Path) -> str:
    suffix = random.SystemRandom().randint(1000, 9999)
    stream = f"runtime-{suffix}"
    other = f"other-{suffix}"
    rows = [
        [stream, 10, "2026-04-02T00:00:00Z", "a", "b", 7000, 0, 0, "S"],
        [stream, 11, "2026-04-02T00:00:01Z", "a", "b", 7001, 0, 40, "PA"],
        [stream, 12, "2026-04-02T00:00:02Z", "a", "b", 7101, 0, 30, "PA"],
        [stream, 13, "2026-04-02T00:00:03Z", "a", "b", 7041, 0, 60, "PA"],
        [stream, 14, "2026-04-02T00:00:04Z", "a", "b", 7001, 0, 40, "PA"],
        [stream, 15, "2026-04-02T00:00:05Z", "a", "b", 7120, 0, 50, "FA"],
        [stream, 16, "2026-04-02T00:00:06Z", "a", "b", 7160, 0, 0, "A"],
        [stream, 17, "2026-04-02T00:00:07Z", "a", "b", 7130, 0, 31, "PA"],
        [stream, 20, "2026-04-02T00:00:00Z", "b", "a", 9000, 0, 0, "S"],
        [stream, 21, "2026-04-02T00:00:01Z", "b", "a", 9001, 0, 20, "PA"],
        [stream, 22, "2026-04-02T00:00:02Z", "b", "a", 9100, 0, 0, "R"],
        [stream, 23, "2026-04-02T00:00:03Z", "b", "a", 500, 0, 5, "PA"],
        [other, 50, "2026-04-02T00:01:00Z", "c", "d", 900, 0, 25, "PA"],
        [other, 51, "2026-04-02T00:01:01Z", "c", "d", 940, 0, 10, "PA"],
        ["", 90, "2026-04-02T00:01:02Z", "x", "y", 1, 0, 1, "PA"],
        [other, "NaN", "2026-04-02T00:01:03Z", "x", "y", 1, 0, 1, "PA"],
        [other, 51, "2026-04-02T00:01:04Z", "c", "d", 950, 0, 1, "PA"],
        [other, 52, "2026-04-02T00:01:05Z", "c", "d", 951, 0, 1, "PX"],
        [other, 53, "2026-04-01T23:59:59Z", "c", "d", 952, 0, 1, "PA"],
        ["short", 1, "too-few"],
    ]
    write_csv(path, rows)
    return stream


def assert_contract_shape(payload: dict) -> None:
    assert list(payload.keys()) == ["input", "streams", "totals", "diagnostics"]
    assert list(payload["input"].keys()) == ["csv", "stream_filter", "rows_read", "rows_skipped"]
    assert list(payload["totals"].keys()) == ["streams", *SUMMARY_KEYS]
    for stream in payload["streams"]:
        assert list(stream.keys()) == ["stream_id", "segments", "gaps", "summary"]
        assert list(stream["summary"].keys()) == SUMMARY_KEYS
        for segment in stream["segments"]:
            assert list(segment.keys()) == [
                "packet_no", "direction", "seq", "end_seq", "payload_len", "flags", "status",
                "expected_before", "gap_before", "fills_gap",
            ]
        for gap in stream["gaps"]:
            assert list(gap.keys()) == ["direction", "start", "end", "length", "introduced_by", "status", "filled_by"]


def test_fixture_classifies_gaps_retransmits_overlap_and_syn(tmp_path: Path) -> None:
    """The shipped fixture exercises gap creation, filling, retransmits, overlaps, and SYN consumption."""
    out_path = tmp_path / "fixture.json"
    actual = run_flowgap(FIXTURE, out_path)
    assert_contract_shape(actual)
    assert actual == expected_payload(FIXTURE)
    alpha = next(stream for stream in actual["streams"] if stream["stream_id"] == "alpha")
    assert [segment["status"] for segment in alpha["segments"]] == [
        "in_order", "out_of_order", "in_order", "retransmit", "overlap",
    ]
    assert alpha["gaps"] == [{
        "direction": "10.0.0.1:45100 -> 10.0.0.2:443",
        "start": 1100,
        "end": 1200,
        "length": 100,
        "introduced_by": 2,
        "status": "filled",
        "filled_by": 3,
    }]


def test_runtime_generated_csv_classification(tmp_path: Path) -> None:
    """Fresh runtime CSV data is classified generically instead of matching the shipped fixture."""
    csv_path = tmp_path / "runtime.csv"
    selected_stream = hidden_csv(csv_path)
    out_all = tmp_path / "all.json"
    actual = run_flowgap(csv_path, out_all)
    assert actual == expected_payload(csv_path)
    selected = next(stream for stream in actual["streams"] if stream["stream_id"] == selected_stream)
    statuses = [segment["status"] for segment in selected["segments"]]
    assert {"out_of_order", "retransmit", "overlap", "zero_length", "reset"}.issubset(set(statuses))
    assert selected["summary"]["directions"] == 2
    assert actual["input"]["rows_read"] == 20
    assert actual["input"]["rows_skipped"] == 6


def test_stream_filter_preserves_global_diagnostics(tmp_path: Path) -> None:
    """A selected stream is the only emitted stream, while malformed rows still appear in diagnostics."""
    csv_path = tmp_path / "runtime.csv"
    selected_stream = hidden_csv(csv_path)
    out_filtered = tmp_path / "filtered.json"
    filtered = run_flowgap(csv_path, out_filtered, selected_stream)
    assert filtered == expected_payload(csv_path, selected_stream)
    assert [stream["stream_id"] for stream in filtered["streams"]] == [selected_stream]
    assert filtered["diagnostics"] == [
        {"row": 16, "error": "blank stream_id"},
        {"row": 17, "error": "invalid integer"},
        {"row": 18, "error": "duplicate packet_no"},
        {"row": 19, "error": "invalid flags"},
        {"row": 20, "error": "timestamp regression"},
        {"row": 21, "error": "wrong column count"},
    ]


def test_repeated_out_of_order_and_cascading_gap_fill(tmp_path: Path) -> None:
    """Repeated out-of-order intervals keep segment gaps but do not duplicate gap records."""
    csv_path = tmp_path / "cascade.csv"
    write_csv(csv_path, [
        ["cascade", 1, "2026-04-03T00:00:00Z", "a", "b", 100, 0, 50, "PA"],
        ["cascade", 2, "2026-04-03T00:00:01Z", "a", "b", 250, 0, 50, "PA"],
        ["cascade", 3, "2026-04-03T00:00:02Z", "a", "b", 250, 0, 30, "PA"],
        ["cascade", 4, "2026-04-03T00:00:03Z", "a", "b", 200, 0, 50, "PA"],
        ["cascade", 5, "2026-04-03T00:00:04Z", "a", "b", 150, 0, 50, "PA"],
        ["cascade", 6, "2026-04-03T00:00:05Z", "a", "b", 125, 0, 200, "PA"],
    ])
    actual = run_flowgap(csv_path, tmp_path / "cascade.json")
    assert actual == expected_payload(csv_path)
    stream = actual["streams"][0]
    assert [segment["status"] for segment in stream["segments"]] == [
        "in_order", "out_of_order", "out_of_order", "out_of_order", "in_order", "overlap",
    ]
    assert stream["segments"][1]["gap_before"] == {"start": 150, "end": 250, "length": 100}
    assert stream["segments"][2]["gap_before"] == {"start": 150, "end": 250, "length": 100}
    assert stream["gaps"] == [
        {"direction": "a -> b", "start": 150, "end": 250, "length": 100, "introduced_by": 2, "status": "filled", "filled_by": 5},
        {"direction": "a -> b", "start": 150, "end": 200, "length": 50, "introduced_by": 4, "status": "filled", "filled_by": 5},
    ]
    assert stream["segments"][4]["fills_gap"] is True
    assert stream["segments"][5]["fills_gap"] is False


def test_bidirectional_state_and_reset_abandons_direction_gap(tmp_path: Path) -> None:
    """Opposite directions in one stream keep independent sequence frontiers, and resets clear one side only."""
    csv_path = tmp_path / "duplex.csv"
    write_csv(csv_path, [
        ["duplex", 1, "2026-04-05T00:00:00Z", "client", "server", 1000, 0, 0, "S"],
        ["duplex", 2, "2026-04-05T00:00:01Z", "server", "client", 5000, 1001, 0, "S"],
        ["duplex", 3, "2026-04-05T00:00:02Z", "client", "server", 1101, 5001, 25, "PA"],
        ["duplex", 4, "2026-04-05T00:00:03Z", "server", "client", 5001, 1126, 30, "PA"],
        ["duplex", 5, "2026-04-05T00:00:04Z", "client", "server", 1001, 5031, 100, "PA"],
        ["duplex", 6, "2026-04-05T00:00:05Z", "client", "server", 1200, 5031, 0, "R"],
        ["duplex", 7, "2026-04-05T00:00:06Z", "client", "server", 77, 0, 10, "PA"],
        ["duplex", 8, "2026-04-05T00:00:07Z", "server", "client", 5031, 1110, 5, "PA"],
    ])
    actual = run_flowgap(csv_path, tmp_path / "duplex.json")
    assert actual == expected_payload(csv_path)
    stream = actual["streams"][0]
    assert stream["summary"]["directions"] == 2
    assert [segment["status"] for segment in stream["segments"]] == [
        "in_order", "in_order", "out_of_order", "in_order", "in_order", "reset", "in_order", "in_order",
    ]
    assert stream["gaps"] == [{
        "direction": "client -> server",
        "start": 1001,
        "end": 1101,
        "length": 100,
        "introduced_by": 3,
        "status": "filled",
        "filled_by": 5,
    }]


def test_reset_abandons_open_gap_and_reinitializes_direction(tmp_path: Path) -> None:
    """A reset abandons open gaps for its direction and the next consuming row starts a new sequence base."""
    csv_path = tmp_path / "reset.csv"
    write_csv(csv_path, [
        ["reset", 1, "2026-04-06T00:00:00Z", "a", "b", 10, 0, 10, "PA"],
        ["reset", 2, "2026-04-06T00:00:01Z", "a", "b", 50, 0, 10, "PA"],
        ["reset", 3, "2026-04-06T00:00:02Z", "a", "b", 20, 0, 0, "R"],
        ["reset", 4, "2026-04-06T00:00:03Z", "a", "b", 1000, 0, 5, "PA"],
        ["reset", 5, "2026-04-06T00:00:04Z", "a", "b", 1005, 0, 0, "A"],
    ])
    actual = run_flowgap(csv_path, tmp_path / "reset.json")
    assert actual == expected_payload(csv_path)
    stream = actual["streams"][0]
    assert [segment["expected_before"] for segment in stream["segments"]] == [10, 20, 20, 1000, 1005]
    assert stream["gaps"] == [{
        "direction": "a -> b",
        "start": 20,
        "end": 50,
        "length": 30,
        "introduced_by": 2,
        "status": "abandoned",
        "filled_by": None,
    }]
    assert stream["summary"]["open_gaps"] == 0
    assert stream["summary"]["abandoned_gaps"] == 1


def test_quoted_csv_blank_lines_and_new_diagnostics(tmp_path: Path) -> None:
    """Quoted fields parse normally, and validation diagnostics keep physical CSV row numbers."""
    csv_path = tmp_path / "quoted.csv"
    write_csv_with_leading_blank(csv_path, [
        ["comma,stream", 1, "2026-04-04T00:00:00Z", "host,one", "dst", 10, 0, 5, "PA"],
        ["comma,stream", 2, "2026-04-04T00:00:01Z", "host,one", "dst", 20, 0, 5, "PA"],
        [],
        ["", 3, "2026-04-04T00:00:02Z", "x", "y", 1, 0, 1, "PA"],
        ["badint", 4, "2026-04-04T00:00:03Z", "x", "y", -1, 0, 1, "PA"],
        ["badflags", 5, "2026-04-04T00:00:04Z", "x", "y", 1, 0, 1, "PR"],
        ["comma,stream", 2, "2026-04-04T00:00:05Z", "host,one", "dst", 25, 0, 5, "PA"],
        ["comma,stream", 6, "2026-04-03T23:59:59Z", "host,one", "dst", 30, 0, 5, "PA"],
        ["short", 5, "too-few"],
    ])

    actual = run_flowgap(csv_path, tmp_path / "quoted.json")
    assert actual == expected_payload(csv_path)
    assert actual["streams"][0]["stream_id"] == "comma,stream"
    assert actual["input"]["rows_read"] == 8
    assert actual["input"]["rows_skipped"] == 6
    assert actual["diagnostics"] == [
        {"row": 6, "error": "blank stream_id"},
        {"row": 7, "error": "invalid integer"},
        {"row": 8, "error": "invalid flags"},
        {"row": 9, "error": "duplicate packet_no"},
        {"row": 10, "error": "timestamp regression"},
        {"row": 11, "error": "wrong column count"},
    ]


def test_empty_stream_filter_preserves_global_diagnostics(tmp_path: Path) -> None:
    """Filtering to an absent stream emits zero totals but keeps CSV-level diagnostics."""
    csv_path = tmp_path / "quoted.csv"
    write_csv_with_leading_blank(csv_path, [
        ["comma,stream", 1, "2026-04-04T00:00:00Z", "host,one", "dst", 10, 0, 5, "PA"],
        ["comma,stream", 2, "2026-04-04T00:00:01Z", "host,one", "dst", 20, 0, 5, "PA"],
        [],
        ["", 3, "2026-04-04T00:00:02Z", "x", "y", 1, 0, 1, "PA"],
        ["badint", 4, "2026-04-04T00:00:03Z", "x", "y", -1, 0, 1, "PA"],
        ["badflags", 5, "2026-04-04T00:00:04Z", "x", "y", 1, 0, 1, "PR"],
        ["short", 5, "too-few"],
    ])
    actual = run_flowgap(csv_path, tmp_path / "quoted.json")
    filtered = run_flowgap(csv_path, tmp_path / "missing.json", "missing-stream")
    assert filtered == expected_payload(csv_path, "missing-stream")
    assert filtered["streams"] == []
    assert filtered["totals"] == {key: 0 for key in ["streams", *SUMMARY_KEYS]}
    assert filtered["diagnostics"] == actual["diagnostics"]


def test_invalid_header_and_flag_errors(tmp_path: Path) -> None:
    """Bad headers and malformed CLI flags fail before producing a JSON contract payload."""
    bad_header = tmp_path / "bad-header.csv"
    bad_header.write_text("stream_id,packet_no\nx,1\n", encoding="utf-8")
    result = subprocess.run(
        [str(BIN), "--csv", str(bad_header), "--out", str(tmp_path / "bad.json")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode != 0
    assert result.stderr == "invalid csv header\n"

    unknown = subprocess.run(
        [str(BIN), "--csv", str(FIXTURE), "--out", str(tmp_path / "out.json"), "--format", "pretty"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert unknown.returncode == 2
    assert unknown.stderr == "usage: flowgap --csv <absolute-path> --out <absolute-path> [--stream <stream_id>]\n"

    missing_value = subprocess.run(
        [str(BIN), "--csv", str(FIXTURE), "--out"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert missing_value.returncode == 2
    assert missing_value.stderr == "usage: flowgap --csv <absolute-path> --out <absolute-path> [--stream <stream_id>]\n"


def test_absolute_path_validation(tmp_path: Path) -> None:
    """Relative input and output paths are rejected with the documented status and stderr text."""
    bad_csv = subprocess.run(
        [str(BIN), "--csv", "relative.csv", "--out", str(tmp_path / "out.json")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert bad_csv.returncode == 2
    assert bad_csv.stderr == "csv path must be absolute: relative.csv\n"

    bad_out = subprocess.run(
        [str(BIN), "--csv", str(FIXTURE), "--out", "summary.json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert bad_out.returncode == 2
    assert bad_out.stderr == "out path must be absolute: summary.json\n"
