# District Review Format

The district review is a final operations summary built from `/app/output/reconciliation-report.json` and `/app/output/settlement-summary.json`.

Assign each reconciliation row to exactly one `review_bucket` using this priority order:

1. `missing_current`: `status` is `missing_from_settlement` and `prior_total_cents` is greater than zero.
2. `new_current`: `status` is `new`.
3. `unadjusted_large_delta`: `status` is `changed`, `adjustment_cents` is zero, the absolute value of `delta_cents` is at least 100, and both `settlement_kwh` and `prior_kwh` are not null with the absolute value of `delta_kwh` at least 0.500.
4. `adjusted_variance`: `adjustment_cents` is not zero and the absolute value of `delta_cents` is at least 5.
5. `usage_swing`: both `settlement_kwh` and `prior_kwh` are not null, and the absolute value of `delta_kwh` is at least 0.500.
6. `routine`: none of the previous rules apply.

Every district entry must include counts for every status key (`changed`, `missing_from_settlement`, `new`, `unchanged`) and every review bucket key (`adjusted_variance`, `missing_current`, `new_current`, `routine`, `unadjusted_large_delta`, `usage_swing`), even when the count is zero.

The exception list should contain only rows whose `review_bucket` is not `routine`. Give exception rows a `priority_score` of 100 for `missing_current`, 80 for `new_current`, 70 for `unadjusted_large_delta`, 60 for `adjusted_variance`, and 40 for `usage_swing`. Sort exceptions by descending `priority_score`, then by service month, account id, and district.

Exception rows should preserve nullable values from the reconciliation row. For example, a `missing_from_settlement` row has no current settlement row, so its exception `final_total_cents` remains null rather than zero. Zero substitution is only for district and overall sums of nullable cent fields.
