The reconciliation report compares the current settlement rows with `/app/prior-ledger/prior-account-months.csv`.

Use the union of keys from both sources. A key is the tuple `(account_id, service_month, district)`. Join manual adjustments from `/app/catalog/meter_catalog.db` table `manual_adjustments` on the same key.

Each row in `/app/output/reconciliation-report.json` should include `account_id`, `service_month`, `district`, `status`, `settlement_total_cents`, `prior_total_cents`, `delta_cents`, `settlement_kwh`, `prior_kwh`, `delta_kwh`, `adjustment_cents`, `adjustment_reason`, and `final_total_cents`.

Set `status` to `new` when the key exists only in the current settlement, `missing_from_settlement` when the key exists only in the prior ledger, `unchanged` when both cents and kWh match exactly, and `changed` otherwise. Use zero as the missing side when calculating deltas. Round `delta_kwh` to three decimals using half-up rounding. If the current settlement row is missing, `settlement_total_cents`, `settlement_kwh`, and `final_total_cents` should be null.
