#!/bin/bash
wrap_ctx() {
  local tag="${1:-}"
  ENV_ROOT="${ENV_ROOT:-/app/environment}"
  local dropin="${ENV_ROOT}/fixtures/wrap_dropin.conf"
  if [[ -f "${dropin}" ]] && grep -q 'NoNewPrivileges=true' "${dropin}"; then
    echo "ctx=svc:${tag}:nnp=1"
  else
    echo "ctx=svc:${tag}:nnp=0"
  fi
}
