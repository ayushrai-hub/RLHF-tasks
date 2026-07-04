#!/bin/bash
set -euo pipefail

# Drives the media signature audit library. Reads configuration from the audit
# contract and invokes the gawk library for the requested stage. All instants are
# handled in UTC.
export TZ=UTC

APP="/app"
CONTRACT="${APP}/config/audit_contract.toml"
LIB="${APP}/lib/media_sig_audit.awk"

cd "${APP}"

usage() {
    echo "usage: audit.sh <catalog|verify|report>" >&2
    exit 2
}

contract_value() {
    python3 - "${CONTRACT}" "$1" <<'PY'
import sys
import tomllib
from pathlib import Path

contract = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
value = contract
for part in sys.argv[2].split("."):
    value = value[part]
if isinstance(value, list):
    print(",".join(str(v) for v in value))
else:
    print(value)
PY
}

stage="${1:-}"
[ -n "${stage}" ] || usage
case "${stage}" in
    catalog|verify|report) ;;
    *) usage ;;
esac

for cmd in gawk openssl sqlite3 python3 curl jq; do
    command -v "${cmd}" >/dev/null 2>&1 || { echo "missing required command: ${cmd}" >&2; exit 1; }
done

# Ensure the local Trust Registry is answering before the library queries it.
"${APP}/bin/start_registry.sh"

DB="$(contract_value database.path)"
SEP="$(contract_value database.separator)"
AUDIT_TIME="$(contract_value time.audit_time)"
SUITE="$(contract_value suite.name)"
REVISION="$(contract_value suite.revision)"
FP_DIGEST="$(contract_value keys.fingerprint_digest)"
PREHASH="$(contract_value keys.prehash_algorithms)"
RAWIN="$(contract_value keys.rawin_algorithms)"
MANIFEST_VERSION="$(contract_value manifest.version)"
RETROACTIVE="$(contract_value revocation.retroactive_reasons)"
REGISTRY_URL="$(contract_value registry.base_url)"
START_CURSOR="$(contract_value registry.start_cursor)"
OUT_CATALOG="$(contract_value outputs.signing_catalog.path)"
OUT_EVIDENCE="$(contract_value outputs.signature_evidence.path)"
OUT_REPORT="$(contract_value outputs.remediation_report.path)"

mkdir -p "${APP}/output" "${APP}/runtime"

gawk \
    -v stage="${stage}" \
    -v db="${DB}" \
    -v sep="${SEP}" \
    -v audit_time="${AUDIT_TIME}" \
    -v suite="${SUITE}" \
    -v revision="${REVISION}" \
    -v fp_digest="${FP_DIGEST}" \
    -v prehash_algos="${PREHASH}" \
    -v rawin_algos="${RAWIN}" \
    -v manifest_version="${MANIFEST_VERSION}" \
    -v retroactive_reasons="${RETROACTIVE}" \
    -v registry_url="${REGISTRY_URL}" \
    -v start_cursor="${START_CURSOR}" \
    -v out_catalog="${OUT_CATALOG}" \
    -v out_evidence="${OUT_EVIDENCE}" \
    -v out_report="${OUT_REPORT}" \
    -f "${LIB}"
