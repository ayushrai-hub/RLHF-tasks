#!/bin/bash
# scheduler-data-mangler
# Every 14 s, swaps room types in /opt/scheduler/rooms.json:
# all "lecture" rooms become "lab" and vice versa.
# This breaks test_room_type_matches (courses get placed in wrong room type).
# Kill EARLY. Restore: cp /var/lib/scheduler-resurrect/rooms.json.bak /opt/scheduler/rooms.json
exec -a scheduler-datmn bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

while true; do
  if [ -f /opt/scheduler/rooms.json ]; then
    sed -i '\''s/"lecture"/"__TMP__"/g; s/"lab"/"lecture"/g; s/"__TMP__"/"lab"/g'\'' \
      /opt/scheduler/rooms.json 2>/dev/null || true
  fi
  sleep 14
done
'
