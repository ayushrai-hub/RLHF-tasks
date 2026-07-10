#!/usr/bin/env bash
set -euo pipefail

app_dir="${TASK_APP_DIR:-/app}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${app_dir}/environment"

if grep -q 'appeal.replay_epoch' src/appeal/replay.rs \
  && grep -q 'LEGAL_ANNOTATIONS.iter().any' src/adjudicate/record.rs; then
  :
else
  patch --forward -p1 < "${script_dir}/fix.patch"
fi
cargo build --quiet --release
mkdir -p "${app_dir}/bin" "${app_dir}/output"
cp target/release/rookline "${app_dir}/bin/rookline"
"${app_dir}/bin/rookline" prove \
  --cases "${app_dir}/environment/fixtures/public_cases.rtl" \
  --out "${app_dir}/output/tournament-appeal-proof.json"
