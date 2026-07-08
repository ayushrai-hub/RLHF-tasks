#!/usr/bin/env bash
# grid_engine.sh <mode> <a> <b>
#
# Validation primitives shared by the public checker.
#
#   grid_engine.sh bind <inventory.json> <report.json>
#       Extracts provenance_digest from the inventory and binding_digest from
#       the report and exits 0 only when the two hex strings are identical.
#
#   grid_engine.sh same <fileA> <fileB>
#       Exits 0 only when the two files are byte-for-byte identical. Used to
#       confirm that a repeated reconciliation is stable.
#
# The digest formula itself is documented in environment/r6/run_contract.md.
set -euo pipefail

mode="${1:?usage: grid_engine.sh <bind|same> <a> <b>}"
a="${2:?missing first path}"
b="${3:?missing second path}"

_digest_of() { # <file> <key>
  grep -oE "\"$2\"[[:space:]]*:[[:space:]]*\"[0-9a-f]{64}\"" "$1" \
    | head -n1 | sed -E 's/.*"([0-9a-f]{64})"/\1/'
}

case "$mode" in
  bind)
    pd="$(_digest_of "$a" provenance_digest)"
    bd="$(_digest_of "$b" binding_digest)"
    [ -n "$pd" ] && [ "$pd" = "$bd" ]
    ;;
  same)
    cmp -s "$a" "$b"
    ;;
  *)
    echo "grid_engine.sh: unknown mode '$mode'" >&2
    exit 64
    ;;
esac
