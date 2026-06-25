#!/usr/bin/env bash
set -uo pipefail

API_DIR="${CASE_API_DIR:-/app/api}"
API_PORT="${CASE_API_PORT:-3000}"
PID_FILE="$(mktemp)"
LOG_FILE="$(mktemp)"

cleanup() {
    if [ -s "$PID_FILE" ]; then
        pid="$(cat "$PID_FILE" 2>/dev/null || true)"
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            pgid="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
            if [ -n "$pgid" ]; then
                kill -TERM -"$pgid" 2>/dev/null || true
            else
                kill -TERM "$pid" 2>/dev/null || true
            fi
            for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
                kill -0 "$pid" 2>/dev/null || break
                sleep 0.2
            done
            if [ -n "$pgid" ]; then
                kill -KILL -"$pgid" 2>/dev/null || true
            fi
            kill -KILL "$pid" 2>/dev/null || true
        fi
    fi
    pkill -KILL -f "puma .*config.ru" 2>/dev/null || true
    sleep 0.2
    rm -f "$PID_FILE" "$LOG_FILE"
}
trap cleanup EXIT INT TERM

mkdir -p /app/output /app/state

START_CMD=(bundle exec puma -C config/puma.rb config.ru)
(
    cd "$API_DIR"
    PORT="$API_PORT" RAILS_ENV="${RAILS_ENV:-production}" \
        setsid "${START_CMD[@]}" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
)

ready=0
for _ in $(seq 1 120); do
    if curl -fsS "http://127.0.0.1:${API_PORT}/healthz" > /dev/null 2>&1; then
        ready=1
        break
    fi
    if [ -s "$PID_FILE" ]; then
        pid="$(cat "$PID_FILE" 2>/dev/null || true)"
        if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
            echo "inquire.sh: puma exited before becoming healthy" >&2
            cat "$LOG_FILE" >&2 || true
            exit 1
        fi
    fi
    sleep 0.5
done

if [ "$ready" -ne 1 ]; then
    echo "inquire.sh: case API never became healthy on port ${API_PORT}" >&2
    cat "$LOG_FILE" >&2 || true
    exit 1
fi

MODE="${1:-play}"
perl "$(dirname "$0")/inquire.pl" "$MODE"
exit "$?"
