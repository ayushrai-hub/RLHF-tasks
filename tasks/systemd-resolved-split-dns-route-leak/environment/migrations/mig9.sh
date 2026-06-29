#!/usr/bin/env bash
set -euo pipefail

ROOT="/app/environment"
ANCHOR="${ROOT}/var/anchor"
STATE="${ROOT}/var/state"
TRACE="${ROOT}/var/trace"
SEED="${ROOT}/fixtures/seed/arena_seed.bin"

if [[ "${1:-}" == "--recover" ]]; then
  seed_path="${2:-$SEED}"
  mkdir -p "$ANCHOR" "$STATE" "$TRACE"
  cp -f "$seed_path" "${ANCHOR}/arena_seed.bin"
  if [[ -f "${ANCHOR}/lane.epoch" ]]; then
    cp -f "${ANCHOR}/lane.epoch" "${STATE}/lane.epoch"
  else
    cp -f "$seed_path" "${ANCHOR}/lane.epoch"
    cp -f "$seed_path" "${STATE}/lane.epoch"
  fi
  exit 0
fi

rm -rf "$STATE" "$TRACE"
mkdir -p "$STATE" "$TRACE"
exit 0
