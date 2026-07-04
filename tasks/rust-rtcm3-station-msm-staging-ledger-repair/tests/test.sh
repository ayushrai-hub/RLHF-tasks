#!/usr/bin/env bash
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
echo '{"version":"1.0.0","results":{"tool":{"name":"pytest"},"summary":{"tests":0,"passed":0,"failed":0,"skipped":0},"tests":[]}}' > /logs/verifier/ctrf.json

if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi
_self="${BASH_SOURCE[0]:-$0}"
_self="${_self//$'\r'/}"
if grep -q $'\r' "$_self" 2>/dev/null; then
  tmp="${TMPDIR:-/tmp}/test-$$.sh"
  tr -d '\r' < "$_self" > "$tmp"
  chmod +x "$tmp"
  exec bash "$tmp" "$@"
fi
set -uo pipefail

export PATH="/opt/verifier-venv/bin:/usr/local/cargo/bin:/usr/bin:${PATH}"
export RUSTUP_HOME="${RUSTUP_HOME:-/usr/local/rustup}"
export CARGO_HOME="${CARGO_HOME:-/usr/local/cargo}"
export CARGO_INCREMENTAL=0

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set." >&2
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

cd /app || {
    echo 0 > /logs/verifier/reward.txt
    exit 1
}

TEST_DIR="${TEST_DIR:-/tests}"

# Agent must rebuild rtcmctl before pytest (cargo build via verifier-rebuild).
/app/scripts/verifier-rebuild.sh || {
    echo 0 > /logs/verifier/reward.txt
    exit 1
}

set +e
/opt/verifier-venv/bin/python -m pytest \
    -o cache_dir=/tmp/pytest_cache \
    --ctrf /logs/verifier/ctrf.json \
    "${TEST_DIR}/test_outputs.py" "${TEST_DIR}/test_tb3_hidden.py" -rA
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
