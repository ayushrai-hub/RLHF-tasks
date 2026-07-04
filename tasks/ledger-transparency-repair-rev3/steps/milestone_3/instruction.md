# Validate Rails Receipts

The Rack transparency service under `/app/service` still exposes broken receipt ids and trusts the broken verifier behavior from before your native library fix. `/app/service/transparency_cli.rb` and `/app/service/transparency_app.rb` must agree with `/app/docs/api_overview.md` and the ceremony contract in `/app/output/ceremony_rules.json`.

Repair the Ruby integration so receipt ids use the documented prefix, `GET /receipts/:seq` returns the correct `{ "receipt_id", "seq" }` pairs, `POST /ledger/validate` accepts every row in `/app/data/ledger_fixture.csv` and rejects tampered or out-of-policy rows, and `GET /ledger/root` returns the chain root computed from the fixture through the repaired native library. Keep `seq` as the raw CSV sequence column string everywhere (for example `"1"`, not integer `1`).

Write `/app/output/validation_report.json` with keys `chain_root`, `receipts` (array of `{ "seq", "receipt_id" }` sorted by seq, with string `seq` values), and `forged_results` (array of `{ "csv_row", "valid" }` with at least one accepted fixture row and two rejected forged rows). Each `valid` value must match what the running Rack app returns from `POST /ledger/validate` for that `csv_row`. Start validation through the running Rack app, not by echoing constants.

Run `bash /tests/test.sh` when this part is done.
