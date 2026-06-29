#!/bin/bash
# offline table writer used by build_all.sh preflight
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

stub_table_append() {
  local src="$1"
  local dest="$2"
  if [[ -f "$src" ]]; then
    cat "$src" >> "$dest"
  fi
}

preflight_table_sink() {
  local out="${TMPDIR:-/tmp}/fvr_preflight.tab"
  : > "$out"
  stub_table_append "${ROOT_DIR}/tables/frag_a.tab" "$out"
  wc -l < "$out"
}
