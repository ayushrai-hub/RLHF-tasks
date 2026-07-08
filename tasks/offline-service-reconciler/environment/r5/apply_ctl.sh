#!/usr/bin/env bash
# apply_ctl.sh <canonical_file> <report_file>
#
# Report cross-check driver. Reads the canonical serialization produced by the
# emit module, derives the provenance digest from it, and stamps that digest
# into the report at the "__BINDING_DIGEST__" slot. The report therefore carries
# a digest that was recomputed independently of the value the inventory writer
# stored, so an inconsistent inventory writer produces a report whose binding
# digest no longer matches the inventory.
#
# The digest is the lowercase SHA-256 hex of the exact bytes of the canonical
# file; see environment/r6/run_contract.md for the canonical layout.
set -euo pipefail

canon="${1:?usage: apply_ctl.sh <canonical_file> <report_file>}"
report="${2:?usage: apply_ctl.sh <canonical_file> <report_file>}"

digest="$(sha256sum "$canon" | awk '{print $1}')"
[ -n "$digest" ] || { echo "apply_ctl.sh: empty digest" >&2; exit 1; }

sed -i "s/__BINDING_DIGEST__/${digest}/" "$report"
