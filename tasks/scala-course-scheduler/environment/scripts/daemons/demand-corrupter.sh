#!/bin/bash
# scheduler-demand-corrupter
# Inflates demand values for high-enrolment courses to 9999 in demand.json every 17 s,
# making them impossible to place in any room (breaks test_room_capacity_sufficient).
# Restore: cp /var/lib/scheduler-resurrect/demand.json.bak /opt/scheduler/demand.json
# comm: "scheduler-dmcor" (15 chars)
exec -a scheduler-dmcor bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
while true; do
  sleep 17
  [ -f /opt/scheduler/demand.json ] && python3 -c "
import json
with open(\"/opt/scheduler/demand.json\") as f: d=json.load(f)
for k in [\"MATH101\",\"PHYS101\",\"PSY101\"]: d[k]=9999
with open(\"/opt/scheduler/demand.json\",\"w\") as f: json.dump(d,f,indent=2)
" 2>/dev/null || true
done
'
