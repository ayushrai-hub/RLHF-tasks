#!/bin/bash
# formats interim q9 rows for diagnostic diff (not authoritative for digest)
stub_emit_rows() {
  local stub_json="$1"
  jq -c '.interim_rows[]' "$stub_json"
}

stub_emit_count() {
  stub_emit_rows "$1" | wc -l
}
