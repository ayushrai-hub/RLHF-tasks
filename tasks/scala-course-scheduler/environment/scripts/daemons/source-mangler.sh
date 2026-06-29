#!/bin/bash
# scheduler-source-mangler
# Every 13 s, re-inserts the .take(16) bug into AuditKeyLoader.scala
# (this is a NON-stub file that source-warden does NOT protect).
# The agent must kill this daemon before fixing Bug D, or it will be re-inserted.
exec -a scheduler-srcma bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

BUGGY=$(cat << '\''EOF_BUGGY'\''
package scheduler.io

import java.nio.file.{Files, Paths}

object AuditKeyLoader:
  def load(path: String): Array[Byte] =
    val all = Files.readAllBytes(Paths.get(path))
    all.take(16)  // BUG-D (re-injected by source-mangler)
EOF_BUGGY
)

while true; do
  if [ -f /app/src/main/scala/scheduler/io/AuditKeyLoader.scala ]; then
    printf "%s\n" "$BUGGY" > /app/src/main/scala/scheduler/io/AuditKeyLoader.scala 2>/dev/null || true
  fi
  sleep 13
done
'
