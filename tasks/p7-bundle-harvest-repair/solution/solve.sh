#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '[solve] %s\n' "$1"; }

cd /app
rm -rf /app/output/p7_bundle
mkdir -p /app/output

log "start json service"
/app/environment/scripts/start_q9_host.sh

log "apply ruby pull fixes"
install -m 0644 "${ROOT_DIR}/patched/t4_lane.rb" "/app/environment/rb/p7_pull/lib/t4_lane.rb"
install -m 0644 "${ROOT_DIR}/patched/r8_mark.rb" "/app/environment/net/r8_mark.rb"
install -m 0644 "${ROOT_DIR}/patched/b3_stat.rb" "/app/environment/rb/p7_pull/lib/b3_stat.rb"

log "install gems"
cd /app/environment/rb/p7_pull && bundle install --quiet

log "run driver"
bundle exec /app/rb/p7_pull/exe/p7_driver --table /app/corpus/m9_table.toml

log "sanity-check bundle"
test -f /app/output/p7_bundle/rollup.toml
test -f /app/output/p7_bundle/s01.csv
test -f /app/output/p7_bundle/bundle.db

python3 <<'PY'
import sqlite3
from pathlib import Path

out = Path("/app/output/p7_bundle")
roll = (out / "rollup.toml").read_text(encoding="utf-8")
assert "bundle_digest" in roll
conn = sqlite3.connect(out / "bundle.db")
n = conn.execute("SELECT COUNT(*) FROM k6_facts").fetchone()[0]
assert n > 0
csv = (out / "s01.csv").read_text(encoding="utf-8").strip().splitlines()
assert len(csv) > 1
PY

log "done"
