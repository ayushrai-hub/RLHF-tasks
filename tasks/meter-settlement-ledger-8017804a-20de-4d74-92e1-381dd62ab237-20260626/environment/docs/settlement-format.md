# Settlement Format

The raw event files under `/app/raw-events` use one JSON object per line. Meter metadata, account energy rates, district credits, district billing windows, peak window settings, local holidays, and billing-band rate adjustments are stored in `/app/catalog/meter_catalog.db`.

Normalized event rows are consumed by downstream billing systems as JSON Lines. Settlement output is split between a SQLite database for account-month lookup and a JSON summary for daily review.

The `district_billing_windows` table defines how service months are assigned after a meter's district is known. Add `utc_offset_hours` to the UTC observation timestamp and compare the resulting local day and hour to `cutover_day` and `cutover_hour`. If the local timestamp is before that monthly cutover, assign the event to the previous local month. Otherwise use the local month.

The `district_peak_windows` table defines local peak hours for the event's district. A normalized row is `peak` only when the local day is Monday through Friday, the local date is not listed in `district_holidays`, and the local hour is greater than or equal to `peak_start_hour` and less than `peak_end_hour`. Otherwise the row is `standard`.

Most raw rows carry interval usage in `kwh`. Rows with `reading_type` set to `register` instead carry a cumulative `register_kwh` value. For those rows, derive interval kWh from the previous accepted register value for the same meter, starting from `meter_register_baselines`. If the current register value is lower than the previous one, add `rollover_kwh` before subtracting the previous value.

The `account_rates` table is a rate schedule. For each normalized row, use the rate with the matching `account_id` and the latest `effective_month` that is less than or equal to the row's `service_month`. Add the matching `district_rate_adjustments.adjustment_cents_per_kwh` for the row's district and billing band. Settlement energy charges are calculated from this row-level effective rate and rounded only after summing the account-month charge.

Reconciliation is a separate final review step. It compares the current account-month settlement rows with the prior ledger snapshot and applies manual adjustments from the catalog database without changing the settlement database.
