#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi
set -euo pipefail

ORACLE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf '== abac framed wire oracle prep ==\n'
head -n 12 /app/docs/abwf-frame-format.md
head -n 10 /app/docs/abac-policy-rules.md
sed -n '1,12p' /app/docs/audit-report-schema.md
grep -n 'eval_seq\|deny-overrides\|fail-closed' /app/docs/abac-policy-rules.md | head -n 5
grep -n 'abac-serve\|--db\|--listen' /app/docs/cli-reference.md | head -n 8
ls -la "${ORACLE_ROOT}/prebuilt/"

printf '== install reference coordinator jar ==\n'
install -m 0644 "${ORACLE_ROOT}/prebuilt/app.jar" /app/bin/app.jar

python3 /app/data/regenerate_sample_abwf.py

SMOKE_DB=/tmp/abac-oracle-smoke.db
SMOKE_OUT=/app/output/abac-constraint-audit.json
rm -f "${SMOKE_DB}" "${SMOKE_OUT}"
mkdir -p /app/output

/app/bin/abac-ingest --db "${SMOKE_DB}" --batch /app/data/sample-policy.abwf
/app/bin/abac-export --db "${SMOKE_DB}" --tenant TEN --out "${SMOKE_OUT}"
test -s "${SMOKE_OUT}"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert d.get('audit_hash')" "${SMOKE_OUT}"

printf '== abac oracle sealed ==\n'
