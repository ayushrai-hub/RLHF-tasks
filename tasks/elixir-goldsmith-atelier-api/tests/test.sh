#!/usr/bin/env bash
set -uo pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

# Kill any old server FIRST so it can't hold the DB file open while we
# delete it (deleting the file under a live server leaves it with an
# orphaned descriptor → "disk I/O error" on every subsequent query).
pkill -f "elixir .* -S mix run" >/dev/null 2>&1 || true
sleep 1

# Reset the DB so the suite always starts from a known seed.
bash /app/scripts/reset_db.sh >/dev/null 2>&1 || true

# (Re)start the server. start.sh is idempotent and waits on /health.
bash /app/start.sh || true

/opt/test-venv/bin/pytest -v -rA --json-report --json-report-file=/tmp/report.json /tests/test_outputs.py
RC=$?

if [ "$RC" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
