#!/usr/bin/env bash
# Module A of the w7 toolchain.
# op_a: read the r1, r2, and r3 surfaces and print one normalized claim row per
# considered claim, tagged with its surface. Row layout is in run_contract.md.
op_a() {
  local ENV_ROOT dec f
  ENV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  dec="$ENV_ROOT/r4/dec0.sh"

  for f in "$ENV_ROOT"/r1/*.json; do
    "$dec" "$f" | while IFS=$'\t' read -r id epoch role region action; do
      printf 'r1\t%s\t%s\t%s\t%s\t%s\n' "$id" "$epoch" "$role" "$region" "$action"
    done
  done

  "$ENV_ROOT/r4/verify_sig.sh" "$ENV_ROOT/r2/base0.json" "$ENV_ROOT/r2/base0.sig"
  "$dec" "$ENV_ROOT/r2/base0.json" | while IFS=$'\t' read -r id epoch role region action; do
    printf 'r2\t%s\t%s\t%s\t%s\t%s\n' "$id" "$epoch" "$role" "$region" "$action"
  done

  for f in "$ENV_ROOT"/r3/ov0.json "$ENV_ROOT"/r3/ov1.json; do
    "$dec" "$f" | while IFS=$'\t' read -r id epoch role region action; do
      printf 'r3\t%s\t%s\t%s\t%s\t%s\n' "$id" "$epoch" "$role" "$region" "$action"
    done
  done
}
