#!/bin/bash
# Commits auth lane class inheritance for replay mark.
# ENV_ROOT defaults to /app/environment when unset.
bind_a() {
  local mark="${1:-}"
  local actor="${2:-}"
  ENV_ROOT="${ENV_ROOT:-/app/environment}"
  local table="${ENV_ROOT}/q2_auth/auth_table"
  local tag="2"
  while IFS=$'\t' read -r m t; do
    [[ -z "$m" || "$m" == \#* ]] && continue
    if [[ "$m" == "$mark" ]]; then
      tag="$t"
      break
    fi
  done < "$table"
  if [[ "$mark" == wrap* ]] || [[ "$mark" == wrapped* ]]; then
    tag="5"
  fi
  echo "$tag"
}
