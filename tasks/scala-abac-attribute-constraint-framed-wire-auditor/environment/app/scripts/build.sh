#!/usr/bin/env bash
set -euo pipefail
cd /app
mkdir -p /app/bin
if [[ "${ABAC_BUILD_CHECK:-0}" == "1" ]]; then
  test -f /app/bin/app.jar || { echo "missing /app/bin/app.jar" >&2; exit 1; }
  exit 0
fi
CP="$(printf '%s:' /opt/abac-libs/*.jar)"
mapfile -t SRC < <(find /app/src/main/scala -name '*.scala' | sort)
/opt/scala3/bin/scalac -classpath "${CP}" -d /app/bin/app.jar "${SRC[@]}"
