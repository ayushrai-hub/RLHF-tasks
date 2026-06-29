#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT_DIR

source "${ROOT_DIR}/lib/t2/row_sink.sh"
source "${ROOT_DIR}/cfg/g3/slot_carry.sh"
source "${ROOT_DIR}/lib/h4/fan_emit.sh"

TABLE_DIR="${ROOT_DIR}/tables"
UNIT_DIR="${ROOT_DIR}/units"
WORK="${TMPDIR:-/tmp}/fvr_work"
mkdir -p "$WORK"

run_lane_profile() {
  local profile_path="$1"
  local lane_id frags_csv unit_frag blk_slice reorder duplicate_recovery
  lane_id=$(jq -r '.lane_id' "$profile_path")
  frags_csv=$(jq -r '.fragments | join(" ")' "$profile_path")
  unit_frag=$(jq -r '.unit_frag' "$profile_path")
  blk_slice=$(jq -r '.blk_slice' "$profile_path")
  reorder=$(jq -r '.reorder_bind // false' "$profile_path")
  duplicate_recovery=$(jq -r '.duplicate_recovery // false' "$profile_path")
  # shellcheck disable=SC2206
  local frags=($frags_csv)

  local table_file="${WORK}/table_${lane_id}.txt"
  op_table_t2 "$TABLE_DIR" "${frags[@]}" > "$table_file"
  local unit_file="${WORK}/unit_${lane_id}.txt"
  if [[ -f "${ROOT_DIR}/lib/h4/stub_emit.sh" ]]; then
    # shellcheck source=/dev/null
    source "${ROOT_DIR}/lib/h4/stub_emit.sh"
    stub_emit_rows "${ROOT_DIR}/fixtures/q9/p9_stub.json" > "${WORK}/stub_${lane_id}.json" || true
  fi
  op_unit_g3 "$table_file" "${UNIT_DIR}/${unit_frag}" "$TABLE_DIR" > "$unit_file"
  local final_file="${WORK}/final_${lane_id}.txt"
  if [[ "$reorder" == "true" ]]; then
    export FVR_REORDER_BIND=1
  else
    unset FVR_REORDER_BIND
  fi
  FVR_BLK_SLICE="${ROOT_DIR}/fixtures/blk/${blk_slice}" op_lane_h4 "$unit_file" > "$final_file"
  if [[ "$duplicate_recovery" == "true" ]]; then
    FVR_BLK_SLICE="${ROOT_DIR}/fixtures/blk/${blk_slice}" op_lane_h4 "$final_file" > "${final_file}.pass2"
    mv "${final_file}.pass2" "$final_file"
  fi

  python3 - "$lane_id" "$final_file" "$profile_path" "${UNIT_DIR}/${unit_frag}" <<'PY'
import hashlib, json, sys
from pathlib import Path

lane_id, final_file, profile_path, unit_path = sys.argv[1:5]
root = Path("/app/environment")
unit_slots = json.loads(Path(unit_path).read_text()).get("slots", {})
rows = []
for line in Path(final_file).read_text().splitlines():
    if not line.strip():
        continue
    slot, parent, opts, path, tail = line.split("|", 4)
    opt = {"opts": opts}
    od = hashlib.sha256(json.dumps(opt, sort_keys=True).encode()).hexdigest()[:8]
    band = 1
    if "shared" in opts:
        band = 2
    if "slave" in opts:
        band = 3
    rows.append({
        "slot_id": int(slot),
        "parent_slot": int(parent),
        "attach_path": path,
        "option_map": opt,
        "band_class": band,
        "_od": od,
    })
rows.sort(key=lambda r: r["slot_id"])
blk = (root / "fixtures/blk/tc.mnt").read_bytes()[:32]
blk_part = blk.hex()
parts = []
for r in rows:
    parts.append(f"{r['slot_id']}|{r['parent_slot']}|{r['attach_path']}|{r['band_class']}|{r['_od']}")
normalized = "\n".join(parts)
digest = hashlib.sha256((normalized + "|" + blk_part).encode()).hexdigest()[:8]
report_band = rows[-1]["band_class"] if rows else 1
for uopts in unit_slots.values():
    if "slave" in str(uopts):
        report_band = 3
        break
out = {
    "lane_id": lane_id,
    "state_digest": digest,
    "band_class": report_band,
    "interim_trace_ids": [f"t{r['slot_id']}" for r in rows],
    "rows": rows,
}
print(json.dumps(out))
PY
}

write_outputs() {
  local matrix_json="$1"
  mkdir -p /app/output
  python3 - "$matrix_json" <<'PY'
import json, sys
from pathlib import Path
matrix = json.loads(Path(sys.argv[1]).read_text())
primary = next(m for m in matrix if m["lane_id"] == "lane_k1")
records = []
for m in matrix:
    records.append({
        "lane_id": m["lane_id"],
        "state_digest": m["state_digest"],
        "band_class": m["band_class"],
        "interim_trace_ids": m["interim_trace_ids"],
    })
report = {
    "schema_version": 1,
    "command": "verify_k9 --matrix-full",
    "lane_records": records,
    "summary": {
        "run_id": "matrix-full",
        "row_count": len(primary.get("rows", [])),
        "terminal_digest": primary["state_digest"],
    },
}
Path("/app/output/run_report.json").write_text(json.dumps(report, indent=2) + "\n")
PY
}

run_full_matrix() {
  local profiles_dir="${ROOT_DIR}/profiles"
  local matrix_file="${WORK}/matrix.json"
  local items=()
  for prof in "$profiles_dir"/lane_k*.json; do
    items+=("$(run_lane_profile "$prof")")
  done
  printf '%s\n' "${items[@]}" | python3 -c 'import json,sys; print(json.dumps([json.loads(l) for l in sys.stdin if l.strip()]))' > "$matrix_file"
  write_outputs "$matrix_file"
  python3 - "$matrix_file" <<'PY'
import json, sys
from pathlib import Path
matrix = json.loads(Path(sys.argv[1]).read_text())
base = next(m for m in matrix if m["lane_id"] == "lane_k1")["state_digest"]
for m in matrix:
    lid = m["lane_id"]
    if lid in ("lane_k1", "lane_k2", "lane_k3", "lane_k4") and m["state_digest"] != base:
        raise SystemExit(f"lane {lid} digest {m['state_digest']} != {base}")
Path("/tmp/fvr_matrix.ok").write_text("ok")
PY
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  run_full_matrix
fi
