#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/fixed/src/main.cpp" /app/src/main.cpp
/app/scripts/build.sh

tmp_out="$(mktemp /tmp/flowgap-smoke.XXXXXX.json)"
/app/bin/flowgap --csv /app/input/packets.csv --out "$tmp_out"
python3 - "$tmp_out" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
alpha = next(stream for stream in payload["streams"] if stream["stream_id"] == "alpha")
assert [segment["status"] for segment in alpha["segments"]] == [
    "in_order", "out_of_order", "in_order", "retransmit", "overlap"
]
assert alpha["segments"][0]["direction"] == "10.0.0.1:45100 -> 10.0.0.2:443"
assert alpha["gaps"][0]["status"] == "filled"
PY

runtime_csv="$(mktemp /tmp/flowgap-runtime.XXXXXX.csv)"
runtime_out="$(mktemp /tmp/flowgap-runtime.XXXXXX.json)"
cat > "$runtime_csv" <<'CSV'
stream_id,packet_no,ts,src,dst,seq,ack,payload_len,flags
runtime,1,2026-04-02T00:00:00Z,a,b,100,0,50,PA
runtime,2,2026-04-02T00:00:01Z,a,b,200,0,40,PA
runtime,3,2026-04-02T00:00:02Z,a,b,150,0,50,PA
runtime,4,2026-04-02T00:00:03Z,a,b,120,0,100,PA
runtime,5,2026-04-02T00:00:04Z,a,b,100,0,50,PA
runtime,6,2026-04-02T00:00:05Z,b,a,900,0,20,PA
runtime,7,2026-04-02T00:00:06Z,b,a,940,0,20,PA
runtime,8,2026-04-02T00:00:07Z,b,a,920,0,0,R
runtime,9,2026-04-02T00:00:08Z,b,a,10,0,5,PA
,10,2026-04-02T00:00:09Z,a,b,1,0,1,PA
bad,NaN,2026-04-02T00:00:10Z,a,b,1,0,1,PA
runtime,5,2026-04-02T00:00:11Z,a,b,130,0,1,PA
runtime,11,2026-04-02T00:00:12Z,a,b,130,0,1,PX
runtime,12,2026-04-02T00:00:01Z,a,b,131,0,1,PA
CSV
/app/bin/flowgap --csv "$runtime_csv" --out "$runtime_out" --stream runtime
python3 - "$runtime_out" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
stream = payload["streams"][0]
assert payload["input"]["rows_read"] == 14
assert payload["input"]["rows_skipped"] == 5
assert payload["diagnostics"] == [
    {"row": 11, "error": "blank stream_id"},
    {"row": 12, "error": "invalid integer"},
    {"row": 13, "error": "duplicate packet_no"},
    {"row": 14, "error": "invalid flags"},
    {"row": 15, "error": "timestamp regression"},
]
assert [segment["status"] for segment in stream["segments"]] == [
    "in_order", "out_of_order", "in_order", "overlap", "retransmit",
    "in_order", "out_of_order", "reset", "in_order"
]
assert stream["summary"]["directions"] == 2
assert stream["summary"]["reset"] == 1
assert stream["summary"]["abandoned_gaps"] == 1
assert stream["gaps"] == [
    {"direction": "a -> b", "start": 150, "end": 200, "length": 50, "introduced_by": 2, "status": "filled", "filled_by": 3},
    {"direction": "b -> a", "start": 920, "end": 940, "length": 20, "introduced_by": 7, "status": "abandoned", "filled_by": None},
]
PY
