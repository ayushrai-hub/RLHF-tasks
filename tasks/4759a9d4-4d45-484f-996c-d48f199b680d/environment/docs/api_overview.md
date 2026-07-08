# Transparency API Overview

Rack service under `/app/service` exposes:

- `GET /receipts/:seq` returns `{ receipt_id, seq }` derived from the ceremony contract.
- `POST /ledger/validate` with `{ "csv_row": "<full csv line>" }` returns `{ "valid": true|false }`.
- `GET /ledger/root` returns `{ "root": "<hex>" }` for the fixture ledger chain.

`/app/output/validation_report.json` must preserve each fixture row's sequence as the raw CSV string in `receipts[].seq` (for example `"1"`, not integer `1`).

Verification uses `/app/native/libledger_verify.so` through Ruby Fiddle bindings in
`/app/service/transparency_cli.rb`.
