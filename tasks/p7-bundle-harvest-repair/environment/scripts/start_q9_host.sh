#!/usr/bin/env bash
set -euo pipefail

PIDFILE=/tmp/q9_host.pid
LOG=/tmp/q9_host.log

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  exit 0
fi

cd /app/environment/api/q9_host
export RAILS_ENV=development
export BUNDLE_GEMFILE=/app/environment/api/q9_host/Gemfile

nohup bundle exec puma -p 9292 -e development config.ru >"$LOG" 2>&1 &
echo $! >"$PIDFILE"

for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:9292/health >/dev/null 2>&1; then
    exit 0
  fi
  sleep 0.25
done

echo "q9_host failed to become ready" >&2
exit 1
