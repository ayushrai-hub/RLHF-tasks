#!/bin/bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT_DIR}/lib/t2/stub_sink.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/cfg/g3/stub_carry.sh"
preflight_table_sink >/dev/null
bench_carry_pass "${ROOT_DIR}/fixtures/tails/ta_tail.txt" >/dev/null
echo "kit ok"
