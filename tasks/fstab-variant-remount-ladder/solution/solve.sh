#!/bin/bash
set -euo pipefail
cd /app/environment

cat > lib/t2/row_sink.sh <<'EOF'
#!/bin/bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${ROOT_DIR}/lib/t2/types.sh"
source "${ROOT_DIR}/lib/t2/replay.sh"

normalize_opts() {
  local build_key="$1"
  local opts="$2"
  local arms="${ROOT_DIR}/meta/arm_opts.toml"
  if [[ -f "$arms" ]] && grep -q "^\[${build_key}\]" "$arms"; then
    if grep -A2 "^\[${build_key}\]" "$arms" | grep -q 'nofail = true'; then
      if [[ "$opts" != *nofail* ]]; then
        opts="${opts},nofail"
      fi
    fi
  fi
  echo "$opts"
}

row_fields() {
  local row="$1"
  slot="${row%%|*}"
  local rest="${row#*|}"
  parent="${rest%%|*}"
  rest="${rest#*|}"
  opts="${rest%%|*}"
  rest="${rest#*|}"
  mpath="${rest%%|*}"
  tail="${rest#*|}"
}

op_table_t2() {
  local table_dir="$1"
  shift
  local frags=("$@")
  declare -A by_slot=()
  declare -A order=()
  local seq=0
  for frag in "${frags[@]}"; do
    local path="${table_dir}/${frag}"
    local build_key
    build_key=$(read_frag_build_key "$path")
    while IFS= read -r row; do
      [[ -z "$row" ]] && continue
      local slot parent opts mpath tail
      row_fields "$row"
      opts=$(normalize_opts "$build_key" "$opts")
      by_slot["$slot"]="${slot}|${parent}|${opts}|${mpath}|${tail}"
      order["$slot"]=$((seq++))
    done < <(collect_frag_rows "$path")
    seq=$((seq + 100))
  done
  for slot in $(printf '%s\n' "${!by_slot[@]}" | sort -n); do
    echo "${by_slot[$slot]}"
  done
}
EOF

cat > cfg/g3/slot_carry.sh <<'EOF'
#!/bin/bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

row_fields() {
  local row="$1"
  slot="${row%%|*}"
  local rest="${row#*|}"
  parent="${rest%%|*}"
  rest="${rest#*|}"
  opts="${rest%%|*}"
  rest="${rest#*|}"
  mpath="${rest%%|*}"
  tail="${rest#*|}"
}

op_unit_g3() {
  local rows_file="$1"
  local unit_json="$2"
  local table_dir="${3:-${ROOT_DIR}/tables}"
  declare -A by_slot=()
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    local slot="${row%%|*}"
    by_slot["$slot"]="$row"
  done < "$rows_file"
  for frag in "$table_dir"/*.tab; do
    [[ -f "$frag" ]] || continue
    while IFS= read -r row; do
      [[ -z "$row" ]] && continue
      local slot="${row%%|*}"
      by_slot["$slot"]="$row"
    done < <(grep -v '^#' "$frag" | grep -v '^[[:space:]]*$' || true)
  done
  for slot in $(printf '%s\n' "${!by_slot[@]}" | sort -n); do
    local row="${by_slot[$slot]}"
    local parent opts mpath tail
    row_fields "$row"
    local unit_opts tail_hint
    unit_opts=$(jq -r --arg s "$slot" '.slots[$s] // empty' "$unit_json")
    if [[ -n "$unit_opts" && "$unit_opts" != "null" ]]; then
      opts="$unit_opts"
    else
      tail_hint=$(jq -r --arg s "$slot" '.[$s] // empty' "${ROOT_DIR}/fixtures/tails/tb_tail.txt" 2>/dev/null || true)
      if [[ -n "$tail_hint" && "$tail_hint" != "null" ]]; then
        if [[ "$opts" == *bind* && "$tail_hint" == "shared" ]]; then
          opts="bind,shared"
        elif [[ "$tail_hint" == "rw" ]]; then
          opts="rw,relatime"
        else
          opts="$tail_hint"
        fi
      fi
    fi
    echo "${slot}|${parent}|${opts}|${mpath}|${tail}"
  done
}
EOF

cat > lib/h4/fan_emit.sh <<'EOF'
#!/bin/bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

load_workdir_hashes() {
  local blk="$1"
  python3 - "$blk" <<'PY'
import struct, sys
from pathlib import Path
p = Path(sys.argv[1])
b = p.read_bytes()
if b[:4] != b"MNT1":
    raise SystemExit(1)
count = struct.unpack_from("<H", b, 4)[0]
off = 6
for _ in range(count):
    sid, wh = struct.unpack_from("<HI", b, off)
    print(sid, wh)
    off += 6
PY
}

normalize_emit_opts() {
  local opts="$1"
  if [[ "$opts" == *slave* ]]; then
    opts="${opts//slave/}"
    opts="${opts//,,/,}"
    opts="${opts#,}"
    opts="${opts%,}"
    if [[ "$opts" == "rw" ]]; then
      opts="rw,relatime"
    fi
  fi
  echo "$opts"
}

row_fields() {
  local row="$1"
  slot="${row%%|*}"
  local rest="${row#*|}"
  parent="${rest%%|*}"
  rest="${rest#*|}"
  opts="${rest%%|*}"
  rest="${rest#*|}"
  mpath="${rest%%|*}"
  tail="${rest#*|}"
}

op_lane_h4() {
  local rows_file="$1"
  local blk="${FVR_BLK_SLICE:-}"
  declare -A wh=()
  if [[ -f "$blk" ]]; then
    while read -r sid hash; do
      wh["$sid"]="$hash"
    done < <(load_workdir_hashes "$blk")
  fi
  declare -A by_path=()
  declare -A score=()
  local -a ingest=()
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    ingest+=("$row")
  done < "$rows_file"
  if [[ -n "${FVR_REORDER_BIND:-}" ]]; then
  local -a sorted=()
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    sorted+=("$row")
  done < <(printf '%s\n' "${ingest[@]}" | awk -F'|' '{print $0}' | sort -t'|' -k4,4)
  ingest=("${sorted[@]}")
  fi
  for row in "${ingest[@]}"; do
    local slot parent opts mpath tail
    row_fields "$row"
    opts=$(normalize_emit_opts "$opts")
    local s="${wh[$slot]:-0}"
    if [[ -z "${by_path[$mpath]:-}" || ${s:-0} -ge ${score[$mpath]:-0} ]]; then
      by_path[$mpath]="${slot}|${parent}|${opts}|${mpath}|${tail}"
      score[$mpath]="$s"
    fi
  done
  for mpath in $(printf '%s\n' "${!by_path[@]}" | sort); do
    local row="${by_path[$mpath]}"
    local slot="${row%%|*}"
    [[ "$slot" -le 3 ]] || continue
    echo "$row"
  done | sort -t'|' -k1,1n
}
EOF

chmod +x lib/t2/row_sink.sh cfg/g3/slot_carry.sh lib/h4/fan_emit.sh
/app/environment/cmd/verify_k9 --matrix-full
