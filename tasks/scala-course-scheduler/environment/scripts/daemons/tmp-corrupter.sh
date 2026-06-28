#!/bin/bash
# scheduler-tmp-corrupter
# Truncates all .class files under /tmp every 9 s, destroying sbt incremental
# compilation caches.  Kill this daemon before running sbt assembly.
# comm: "scheduler-tmpco" (15 chars)
exec -a scheduler-tmpco bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
while true; do
  find /tmp -name "*.class" 2>/dev/null | while IFS= read -r f; do
    : > "$f" 2>/dev/null || true
  done
  sleep 9
done
'
