#!/bin/bash
# scheduler-data-scrambler
# Corrupts /opt/scheduler/courses.json every 13 s by changing all lab room-type
# requirements to lecture, breaking test_room_type_matches.
# Restore: cp /var/lib/scheduler-resurrect/courses.json.bak /opt/scheduler/courses.json
# comm: "scheduler-dscra" (15 chars)
exec -a scheduler-dscra bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
while true; do
  sleep 13
  [ -f /opt/scheduler/courses.json ] && \
    sed -i '"'"'s/"required_room_type": "lab"/"required_room_type": "lecture"/g'"'"' \
    /opt/scheduler/courses.json 2>/dev/null || true
done
'
