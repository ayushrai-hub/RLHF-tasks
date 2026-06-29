#!/bin/bash
chmod +x /solution/solve.sh /tests/test.sh 2>/dev/null || true
# Container entrypoint: start cron for resurrection fallback, then launch all daemons.
service cron start >/dev/null 2>&1 || true
[ -x /opt/scheduler/daemons/launch-all.sh ] && /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1 || true
exec "$@"
