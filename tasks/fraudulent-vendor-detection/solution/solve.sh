#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

require_tree() {
  local missing=0
  for path in \
    "${ROOT_DIR}/cord/resume_k.go" \
    "${ROOT_DIR}/vault/carry_k.go" \
    "${ROOT_DIR}/span/front_k.go" \
    "${ROOT_DIR}/vm/acc_k.go"
  do
    if [[ ! -f "${path}" ]]; then
      echo "missing oracle source: ${path}" >&2
      missing=1
    fi
  done
  if [[ "${missing}" -ne 0 ]]; then
    exit 1
  fi
}

install_oracle_sources() {
  cp "${ROOT_DIR}/cord/resume_k.go" /app/environment/cord/resume_k.go
  cp "${ROOT_DIR}/vault/carry_k.go" /app/environment/vault/carry_k.go
  cp "${ROOT_DIR}/span/front_k.go" /app/environment/span/front_k.go
  cp "${ROOT_DIR}/vm/acc_k.go" /app/environment/vm/acc_k.go
}

rebuild_runner() {
  export PATH="/usr/local/go/bin:${PATH}"
  cd /app/environment
  if ! go build -trimpath -ldflags="-s -w" -o /app/bin/vendorlab ./cmd/vendorlab; then
    echo "oracle go build failed" >&2
    exit 1
  fi
}

if [[ ! -d /app/environment ]]; then
  echo "environment root missing: /app/environment" >&2
  exit 1
fi

require_tree
install_oracle_sources
rebuild_runner
