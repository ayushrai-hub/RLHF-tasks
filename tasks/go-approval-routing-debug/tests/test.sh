#!/usr/bin/env bash
# Always produce a reward file so the harness never reports
# "verifier_did_not_run". A broken submission scores 0.
set -uo pipefail

mkdir -p /logs/verifier
TESTDIR="$(cd "$(dirname "$0")" && pwd)"

fail() {
    echo "ERROR: $1" >&2
    echo 0 > /logs/verifier/reward.txt
    exit 0
}

export GOFLAGS=-mod=mod
export GOPROXY=off

cd /app/src || fail "source directory /app/src not found"
go build -o /tmp/approval-api . || fail "agent's code does not compile"

# Start the server. Redirect its stdout/stderr to a log file rather than letting
# them stay attached to test.sh's stdout (the harness's pipe): a long-lived
# server still holding that pipe after test.sh exits can keep it from reaching
# EOF, which the harness reports as "verifier_did_not_run". With its own log file
# the server can never hold the harness pipe open regardless of kill timing.
/tmp/approval-api > /tmp/approval-api.log 2>&1 &
SERVER_PID=$!

cleanup() {
    kill "$SERVER_PID" 2>/dev/null || true
    rm -f /app/src/zz_race_test.go
}
trap cleanup EXIT

# Wait (offline, no curl) for the server to accept connections.
READY=false
for i in $(seq 1 40); do
    if python3 - <<'PY' 2>/dev/null
import socket, sys
s = socket.socket()
s.settimeout(0.5)
try:
    s.connect(("127.0.0.1", 8080))
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
    then
        READY=true
        break
    fi
    sleep 0.25
done
[ "$READY" = "true" ] || fail "server did not start within 10 seconds"

# 1) Endpoint behavior.
# Bound pytest: test_api.py issues plain `requests` calls with no per-request
# timeout, so a submission whose server accepts the connection (readiness check
# passed) but then hangs on a specific endpoint would block pytest forever and
# the harness would kill test.sh at the verifier timeout before reward.txt is
# written — surfacing as "verifier_did_not_run" instead of a scored 0.
timeout 120 pytest "$TESTDIR/test_api.py" -v -rA --tb=short
PYTEST_RC=$?

# 2) Concurrency: the service must be clean under the Go race detector. The
#    race test is supplied by the verifier and compiled against the agent's
#    package, so it is independent of where any fix lives.
cp "$TESTDIR/race_test.go" /app/src/zz_race_test.go
# Bound the race gate two ways: an inner `-timeout 90s` so a submission that
# deadlocks under the race detector fails fast instead of running to Go's 10m
# default, and an outer `timeout 150` as a hard backstop on the whole compile+
# run. Either expiry yields a non-zero RACE_RC (124/125) → a scored 0, never a
# verifier_did_not_run from the harness reaping a hung test.sh at 240s.
( cd /app/src && timeout 150 env CGO_ENABLED=1 go test -race -run TestRaceGetUpdate -count=1 -timeout 90s ./... )
RACE_RC=$?
rm -f /app/src/zz_race_test.go

[ "$PYTEST_RC" -eq 0 ] && [ "$RACE_RC" -eq 0 ]
OVERALL_RC=$?
if [ "$OVERALL_RC" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
