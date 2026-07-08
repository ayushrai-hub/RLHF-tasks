#!/usr/bin/env bash
# dec0.sh <file>
#
# Decodes the claim rows carried by a surface file into a normalized, tab
# separated stream. One output row is produced per JSON object that carries an
# "id" field. Columns, in order:
#
#   id <TAB> epoch <TAB> role <TAB> region <TAB> action
#
# A field that is absent from the object is emitted as a single "-". The column
# layout is documented in environment/r6/run_contract.md. This decoder is format
# only: it does not know which surface a file came from and does not apply any
# authority, freshness, or removal decision.
set -u

f="${1:?usage: dec0.sh <file>}"

_field() { # <line> <key> -> value (string or number), empty if missing
  local line="$1" key="$2" v
  v="$(printf '%s' "$line" \
        | grep -oE "\"$key\"[[:space:]]*:[[:space:]]*(\"[^\"]*\"|-?[0-9]+)" \
        | head -n1)" || v=""
  v="${v#*:}"
  printf '%s' "$v" | sed -E 's/^[[:space:]]*//; s/^"//; s/"$//'
}

while IFS= read -r line; do
  case "$line" in
    *'"id"'*) ;;
    *) continue ;;
  esac
  id="$(_field "$line" id)"
  epoch="$(_field "$line" epoch)";   [ -n "$epoch" ]  || epoch="-"
  role="$(_field "$line" role)";     [ -n "$role" ]   || role="-"
  region="$(_field "$line" region)"; [ -n "$region" ] || region="-"
  action="$(_field "$line" action)"; [ -n "$action" ] || action="-"
  # An alias entry names another host to mirror; it is decoded as action=alias
  # with the target carried in the role column.
  alias="$(_field "$line" alias)"
  if [ -n "$alias" ]; then role="$alias"; action="alias"; fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$epoch" "$role" "$region" "$action"
done < "$f"
