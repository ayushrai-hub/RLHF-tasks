#!/bin/bash
# no-op option refresh for offline benchmark harness
stub_carry_refresh() {
  local rows_file="$1"
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    echo "$row"
  done < "$rows_file"
}

bench_carry_pass() {
  stub_carry_refresh "$1" | wc -l
}
