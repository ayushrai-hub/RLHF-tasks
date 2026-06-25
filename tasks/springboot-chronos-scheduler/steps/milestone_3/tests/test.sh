#!/bin/bash
# Milestone 3 verifier — boots the app and runs test_m3.py against the
# concurrent dispatcher, heartbeat, and failover endpoints.
set -uo pipefail

TEST_DIR="${TEST_DIR:-/tests}"
mkdir -p /logs/verifier

cd /app

if [ -f /app/target/chronos.jar ]; then
  cp /app/target/chronos.jar /app/chronos.jar
fi

rm -f /app/data/chronos.mv.db /app/data/chronos.trace.db /app/data/chronos.lock.db
mkdir -p /app/data

# Materialize the schema at the file: path the app reads (application.yml uses
# file:/app/schema.sql, not classpath: — fat-jar classpath: resolution is flaky).
cp -f /app/src/main/resources/schema.sql /app/schema.sql

LOG=/logs/verifier/server-m3.log
java -jar /app/chronos.jar > "$LOG" 2>&1 &
SERVER_PID=$!

cleanup() {
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

READY=0
for i in $(seq 1 60); do
  if curl -fsS http://localhost:8080/health >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "server did not become ready" >&2
  tail -120 "$LOG" >&2 || true
  echo 0 > /logs/verifier/reward.txt
  exit 1
fi

/opt/test-env/bin/pytest \
    -o cache_dir=/tmp/pytest_cache \
    --ctrf /logs/verifier/ctrf.json \
    "$TEST_DIR/test_m3.py" -rA

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
