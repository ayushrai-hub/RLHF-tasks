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

op_table_t2() {
  local table_dir="$1"
  shift
  local frags=("$@")
  local merged=()
  local arms="${ROOT_DIR}/meta/arm_opts.toml"
  for frag in "${frags[@]}"; do
    local path="${table_dir}/${frag}"
    local build_key
    build_key=$(read_frag_build_key "$path")
    if [[ -f "$arms" ]] && grep -q "^\[k99\]" "$arms"; then
      build_key="k99"
    fi
    while IFS= read -r row; do
      [[ -z "$row" ]] && continue
      local slot parent opts mpath tail
      IFS='|' read -r slot parent opts mpath tail <<< "$row"
      opts=$(normalize_opts "$build_key" "$opts")
      merged+=("${slot}|${parent}|${opts}|${mpath}|${tail}")
    done < <(collect_frag_rows "$path")
  done
  printf '%s\n' "${merged[@]}"
}
