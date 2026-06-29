#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="/app"

echo "== Milestone 1: load contracts =="
for doc in overview.md field-classification.md block-loading.md staging-pipeline.md manifest-and-seal.md; do
  test -f "${APP}/docs/${doc}" || { echo "Missing ${APP}/docs/${doc}" >&2; exit 1; }
  echo "  contract: ${APP}/docs/${doc}"
done

echo "== Milestone 1: add sealed export modules =="
cp "${DIR}/files/field_rules.py" "${APP}/field_rules.py"
cp "${DIR}/files/block_parser.py" "${APP}/block_parser.py"
cp "${DIR}/files/staging_lineage.py" "${APP}/staging_lineage.py"
cp "${DIR}/files/block_stager.py" "${APP}/block_stager.py"
cp "${DIR}/files/export_metadata.py" "${APP}/export_metadata.py"
cp "${DIR}/files/export_builder.py" "${APP}/export_builder.py"
cp "${DIR}/files/secret_manifest.py" "${APP}/secret_manifest.py"
cp "${DIR}/files/seal_canonical.py" "${APP}/seal_canonical.py"
cp "${DIR}/files/integrity_seal.py" "${APP}/integrity_seal.py"
cp "${DIR}/files/replay_journal.py" "${APP}/replay_journal.py"

echo "Milestone 1 oracle complete."
