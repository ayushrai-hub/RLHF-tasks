#!/usr/bin/env bash
# Usage: reads normalized claim rows on stdin.
#
# Naive selector. Reads normalized claim rows
# (id<TAB>epoch<TAB>role<TAB>region<TAB>action) on stdin and, for each id, keeps
# whichever row appears last in the stream. It pays no attention to which surface
# a row came from and none to the recorded epoch, so it behaves like a
# last-writer pass. It is wired into no pipeline.
set -euo pipefail

declare -A last
order=()
while IFS=$'\t' read -r id epoch role region action; do
  [ -z "${id:-}" ] && continue
  if [ -z "${last[$id]+x}" ]; then order+=("$id"); fi
  last[$id]="$id	$epoch	$role	$region	$action"
done

for id in "${order[@]}"; do
  printf '%s\n' "${last[$id]}"
done
