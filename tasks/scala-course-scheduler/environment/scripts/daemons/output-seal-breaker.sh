#!/bin/bash
# scheduler-output-seal-breaker
# Every 16 s, if schedule.json exists, replaces the session_seal field with
# 64 zero hex chars.  Kill this daemon before and after running the JAR.
# comm: "scheduler-osbr" (14 chars — fits /proc/comm)
exec -a scheduler-osbr bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
while true; do
  if [ -f /opt/scheduler/schedule.json ]; then
    python3 - /opt/scheduler/schedule.json 2>/dev/null << '"'"'PYEOF'"'"'
import json, sys
p = sys.argv[1]
try:
    with open(p) as f: d = json.load(f)
    d["session_seal"] = "0" * 64
    with open(p, "w") as f: json.dump(d, f, indent=2)
except Exception: pass
PYEOF
  fi
  sleep 16
done
'
