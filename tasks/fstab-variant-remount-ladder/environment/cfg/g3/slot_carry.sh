#!/bin/bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

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
      if [[ -z "${by_slot[$slot]:-}" ]]; then
        by_slot["$slot"]="$row"
      fi
    done < <(grep -v '^#' "$frag" | grep -v '^[[:space:]]*$' || true)
  done
  for slot in $(printf '%s\n' "${!by_slot[@]}" | sort -n); do
    local row="${by_slot[$slot]}"
    local parent opts mpath tail
    IFS='|' read -r slot parent opts mpath tail <<< "$row"
    local unit_opts
    unit_opts=$(jq -r --arg s "$slot" '.slots[$s] // empty' "$unit_json")
    if [[ -n "$unit_opts" && "$unit_opts" != "null" ]]; then
      opts="$unit_opts"
    fi
    echo "${slot}|${parent}|${opts}|${mpath}|${tail}"
  done
}
