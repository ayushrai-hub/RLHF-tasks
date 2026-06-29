#!/bin/bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

read_frag_build_key() {
  local path="$1"
  grep -m1 '^# build_key=' "$path" | cut -d= -f2
}

collect_frag_rows() {
  local path="$1"
  grep -v '^#' "$path" | grep -v '^[[:space:]]*$' || true
}
