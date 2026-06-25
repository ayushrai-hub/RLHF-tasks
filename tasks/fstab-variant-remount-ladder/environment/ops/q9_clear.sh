#!/bin/bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rm -f /tmp/fvr_work/* 2>/dev/null || true
epoch_file="${ROOT_DIR}/meta/epoch.marker"
if [[ -f "$epoch_file" ]]; then
  echo $(( $(cat "$epoch_file") + 1 )) > "$epoch_file"
else
  echo 1 > "$epoch_file"
fi
