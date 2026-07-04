#!/bin/bash
set -euo pipefail
OUT="/app/output/search-run.json"
/app/environment/scripts/run_search.sh /app/environment/configs/public-plan.json "$OUT"
python3 - <<'PYVERIFY'
import json
from pathlib import Path
out = json.loads(Path('/app/output/search-run.json').read_text())
assert out['schema_version'] == 'offline-search-run-v1'
assert out['snapshot_hash'].startswith('sha256:')
qs = {q['id']: q for q in out['queries']}
solar = qs['q-solar']['results']
assert solar and solar[0]['canonical_url'] == 'https://example.com/solar-inverter-guide', solar
assert all('old.example.com' not in r['canonical_url'] for r in solar), solar
assert all('mirror.example.net' not in u for r in solar for u in r['supporting_urls']), solar
reef = qs['q-reef']['results']
assert reef and reef[0]['canonical_url'] == 'https://coast.example.com/reef-lantern', reef
assert all(seg['snapshot_hash'] == out['snapshot_hash'] for seg in out['provenance']['segments'])
print('public search contract passed')
PYVERIFY
