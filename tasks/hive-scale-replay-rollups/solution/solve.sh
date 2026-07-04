#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd /app

for module in frame manifest config replay state window rollup report main; do
  src="$ROOT_DIR/fixed/${module}.rs"
  if [ ! -f "$src" ]; then
    echo "missing fixed module: $module" >&2
    exit 1
  fi
  cp "$src" "src/${module}.rs"
done

if command -v cargo >/dev/null 2>&1; then
  cargo fmt 2>/dev/null || true
fi

cargo build --release --locked
install target/release/hive_scale /app/bin/hive_scale

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

STATE="$TMP_DIR/state"
mkdir -p "$STATE"
DAILY="$TMP_DIR/daily.jsonl"
SUMMARY="$TMP_DIR/summary.json"
QUAR="$TMP_DIR/quarantine.jsonl"

/app/bin/hive_scale \
  --manifest /app/fixtures/manifests/demo_part1.json \
  --config /app/config/apiary.toml \
  --state-dir "$STATE" \
  --emit-daily "$DAILY" \
  --emit-summary "$SUMMARY" \
  --emit-quarantine "$QUAR"

DAILY2="$TMP_DIR/daily2.jsonl"
SUMMARY2="$TMP_DIR/summary2.json"
QUAR2="$TMP_DIR/quarantine2.jsonl"

echo "stale snapshot bytes" > "$STATE/rollup_state.json.tmp"

/app/bin/hive_scale \
  --manifest /app/fixtures/manifests/demo_part2.json \
  --config /app/config/apiary.toml \
  --state-dir "$STATE" \
  --emit-daily "$DAILY2" \
  --emit-summary "$SUMMARY2" \
  --emit-quarantine "$QUAR2" \
  --resume

test -s "$DAILY"
test -s "$DAILY2"
test -s "$SUMMARY"
test -s "$SUMMARY2"
