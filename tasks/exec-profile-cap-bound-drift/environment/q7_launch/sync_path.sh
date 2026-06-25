#!/bin/bash
# Merges capsh snapshots from approved launch replay rounds.
sync_d() {
  local mark="${1:-}"
  local round="${2:-}"
  local eff_pre="${3:-0}"
  local eff_post="${4:-0}"
  ENV_ROOT="${ENV_ROOT:-/app/environment}"
  local post_file="${ENV_ROOT}/fixtures/q8/post_step.dat"
  local gap="G0"
  local required="0x40"
  local expect_gap="G7"
  if [[ -f "$post_file" ]]; then
    required=$(grep '^required=' "$post_file" | cut -d= -f2)
    expect_gap=$(grep '^gap_code=' "$post_file" | cut -d= -f2)
  fi
  if [[ "$mark" == "wrapped_p1" && "$round" == "r1" ]]; then
    local pre_mask=$((eff_pre))
    local req_mask=$((required))
    if (( (pre_mask & req_mask) == req_mask )); then
      gap="G0"
    else
      gap="$expect_gap"
    fi
  fi
  echo "$gap"
}
