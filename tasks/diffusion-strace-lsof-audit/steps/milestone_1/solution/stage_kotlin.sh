#!/bin/bash
set -euo pipefail

usage() {
  echo "usage: stage_kotlin.sh <oracle_dir> <Symbol> ..." >&2
  exit 2
}

[[ $# -ge 2 ]] || usage

oracle_dir="$1"
shift

if [[ ! -d "$oracle_dir" ]]; then
  echo "oracle directory missing: $oracle_dir" >&2
  exit 1
fi

for symbol in "$@"; do
  src="${oracle_dir}/${symbol}.kt"
  if [[ ! -f "$src" ]]; then
    echo "oracle source missing: $src" >&2
    exit 1
  fi
  if [[ ! -s "$src" ]]; then
    echo "oracle source empty: $src" >&2
    exit 1
  fi
done
