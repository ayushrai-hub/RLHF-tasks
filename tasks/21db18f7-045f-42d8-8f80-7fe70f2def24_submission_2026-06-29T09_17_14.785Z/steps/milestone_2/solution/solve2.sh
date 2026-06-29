#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="/app"

echo "== Milestone 2: load contracts =="
for doc in overview.md crypto-contract.md derivation-notes.md; do
  test -f "${APP}/docs/${doc}" || { echo "Missing ${APP}/docs/${doc}" >&2; exit 1; }
  echo "  contract: ${APP}/docs/${doc}"
done

echo "== Milestone 2: add field crypto modules =="
cp "${DIR}/files/derivation_registry.py" "${APP}/derivation_registry.py"
cp "${DIR}/files/hkdf_params.py" "${APP}/hkdf_params.py"
cp "${DIR}/files/key_derivation.py" "${APP}/key_derivation.py"
cp "${DIR}/files/crypto_nonce_policy.py" "${APP}/crypto_nonce_policy.py"
cp "${DIR}/files/aes_crypto.py" "${APP}/aes_crypto.py"

echo "Milestone 2 oracle complete."
