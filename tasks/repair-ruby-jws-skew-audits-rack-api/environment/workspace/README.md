# StampGate classroom workspace

Repair the Ruby `stampgate-audit` CLI and run JWS skew audits against the Rack policy API on port 8966.

## Layout

| Path | Purpose |
|------|---------|
| `/workspace/stampgate-lib/bin/stampgate-audit` | Audit CLI entrypoint |
| `/workspace/stampgate-lib/lib/stamp_gate/` | Ruby library modules |
| `/workspace/stampgate-api/app.rb` | Policy API service |
| `/workspace/data/assertion-ledger.csv` | Assertion ledger fixture |
| `/workspace/data/stampgate-policy.sqlite` | Authoritative policy database |
| `/workspace/data/nonce-cache.sqlite` | Replay nonce store |
| `/workspace/schemas/` | JSON Schema contracts |
| `/workspace/docs/` | Operator handbook and API reference |

## Documentation index

Start at `/workspace/docs/handover-index.md` for milestone-specific reading order.

## Outputs

| Artifact | Command |
|----------|---------|
| `policy-cache.json` | `stampgate-audit policy` |
| `jws-window-check.json` | `stampgate-audit verify` |
| `jws-audit-report.json` | `stampgate-audit report` |

Validate every JSON artifact against its schema under `/workspace/schemas/`.
