#!/usr/bin/env bash
set -uo pipefail

cd /app
mkdir -p /app/data /app/logs

# Build only if the build artefacts are missing — repeated invocations stay cheap.
if [ ! -d /app/_build/prod/lib/goldsmith ]; then
    MIX_ENV=prod mix compile 2>&1 | tee /app/logs/build.log || {
        echo "compile failed; see /app/logs/build.log" >&2
        exit 2
    }
fi

# If a server is already listening, leave it alone — idempotent restarts.
if python3 -c \
    "import socket; s=socket.socket(); s.settimeout(0.5); s.connect(('127.0.0.1', 8080)); s.close()" \
    >/dev/null 2>&1; then
    echo "goldsmith already listening on :8080" >&2
    exit 0
fi

# Background the server so start.sh returns promptly.
nohup env MIX_ENV=prod elixir --no-halt -S mix run \
      >/app/logs/server.log 2>&1 </dev/null &
disown || true

# Spin until /health answers — bounded by 40 attempts at 0.5s.
for _ in $(seq 1 40); do
    if python3 -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=1)" \
        >/dev/null 2>&1; then
        echo "goldsmith healthy" >&2
        exit 0
    fi
    sleep 0.5
done

echo "goldsmith did not become healthy in 20s — see /app/logs/server.log" >&2
exit 1
