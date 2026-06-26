#!/usr/bin/env bash
set -euo pipefail
cd /app

mkdir -p /app/bin

if [[ "${VAULT_BUILD_CHECK:-0}" == "1" ]]; then
  test -f /app/bin/app.jar || {
    echo "missing /app/bin/app.jar (run /app/scripts/build.sh without VAULT_BUILD_CHECK)" >&2
    exit 1
  }
  exit 0
fi

CP="/opt/scala3/lib/*:$(printf '%s:' /opt/vault-libs/*.jar)"
mapfile -t SRC < <(find /app/src/main/scala -name '*.scala' | sort)

/opt/scala3/bin/scalac -classpath "${CP}" -d /app/bin/app.jar "${SRC[@]}"
