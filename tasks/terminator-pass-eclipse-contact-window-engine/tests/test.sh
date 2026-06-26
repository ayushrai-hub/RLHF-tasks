#!/usr/bin/env bash
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
CTRF_DIR=/logs/verifier/ctrf
CTRF="$CTRF_DIR/ctrf.json"
mkdir -p "$CTRF_DIR"
finish() {
    if [ ! -f "$CTRF" ]; then
        echo '{"results":{"tool":{"name":"pytest"},"summary":{"tests":0,"passed":0,"failed":0,"skipped":0,"pending":0,"other":0},"tests":[]}}' > "$CTRF"
    fi
    if [ -n "${PID:-}" ]; then
        kill "$PID" 2>/dev/null || true
    fi
}
trap finish EXIT
export PATH="$PATH:/usr/local/go/bin"
cd /app
if ! (make clean && make build); then
    echo "Build failed" >&2
    exit 1
fi
bash /app/bin/start.sh &
PID=$!
ready=0
for _ in $(seq 1 60); do
    if python3 - <<'PY'
import json
import urllib.request

try:
    with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=1) as response:
        payload = json.loads(response.read())
    raise SystemExit(0 if payload.get("ok") is True else 1)
except Exception:
    raise SystemExit(1)
PY
    then
        ready=1
        break
    fi
    sleep 0.25
done
if [ "$ready" -eq 0 ]; then
    echo "server did not become healthy" >&2
    exit 1
fi
cd /tests
python3 -m pytest test_outputs.py -v -rA --tb=short --ctrf "$CTRF"
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
