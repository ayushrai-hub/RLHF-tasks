#!/bin/bash
# Build the course-scheduler fat JAR and copy it to /opt/scheduler/scheduler.jar.
#
# IMPORTANT — DO NOT type `sbt` on its own.  That drops into the sbt REPL
# and any subsequent shell keystroke is interpreted as an sbt command
# (e.g. `-q` becomes a parse error; arbitrary words fail with "Expected ID
# character" and can deadlock the harness send_keys layer).  Always invoke
# sbt with a single-shot quoted command, as this script does.
set -euo pipefail

cd /app
echo "==> sbt assembly (single-shot, no REPL)"
sbt -batch -Dsbt.color=false 'assembly'

JAR=target/scala-3.3.4/scheduler.jar
if [ ! -f "$JAR" ]; then
  echo "ERROR: $JAR not produced by sbt assembly" >&2
  exit 1
fi
mkdir -p /opt/scheduler
cp "$JAR" /opt/scheduler/scheduler.jar
echo "==> Build complete: /opt/scheduler/scheduler.jar"
