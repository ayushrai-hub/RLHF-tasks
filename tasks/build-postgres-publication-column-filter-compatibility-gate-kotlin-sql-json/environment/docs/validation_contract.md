The validation report has keys `summary` and `results`.

The summary contains `subscriptions`, `checkedTables`, `compatible`, `blocked`, and `diagnostics`. Results are sorted by subscription, table, and publication. Validation results are created from subscriber target tables only; a publication table that no subscriber targets does not create its own result row. Each result contains `subscription`, `publication`, `table`, `status`, `publishedColumns`, `subscriberColumns`, and `diagnostics`; `table` is always schema-qualified as `schema.name`, such as `public.accounts`. Status is `compatible` only when diagnostics is empty. `publishedColumns` and `subscriberColumns` are sorted alphabetically in ascending order. `publishedColumns` is empty only when the table is absent from the publication or the publication sends every publisher column.

Diagnostic objects contain `code`, `severity`, and `message`. Column-specific diagnostics also contain `missingColumns`, sorted ascending. For example, an unsafe filter that omits `total_cents` is represented with `"code": "unsafe_filter"` and `"missingColumns": ["total_cents"]`; the field is named `missingColumns`, not `columns`.

Diagnostic codes are `missing_publication`, `missing_table`, `missing_column`, `unsafe_filter`, `primary_key_omitted`, and `identity_filter_blocked`. Every diagnostic code in this report uses severity `blocking`; missing objects, schema gaps, unsafe filters, omitted primary keys, and filtered `REPLICA IDENTITY FULL` tables all block the cutover gate. `missing_table` is emitted for each missing table relationship independently: once when the subscriber target table is not listed in the referenced publication, and once when that same target table is absent from the publisher schema. A publication column list must contain every subscriber column for that table. If a subscriber column is absent from the publisher schema and absent from a filtered publication column list, the same column appears in both the `missing_column` and `unsafe_filter` diagnostics. If a filtered table has primary key columns, those key columns must be included. A table using `REPLICA IDENTITY FULL` is blocked when its publication uses a column list.

Within one validation result, diagnostics are ordered by relationship and then column-safety checks: `missing_publication` or the publication-membership `missing_table`, then the publisher-schema `missing_table`, then `missing_column`, `unsafe_filter`, `primary_key_omitted`, and `identity_filter_blocked`. This keeps repeated `missing_table` diagnostics in the same order as their meanings: absent from publication first, absent from publisher schema second.

Messages should be short human-readable sentences, and these substrings are required for compatibility with the release gate:

- `missing_publication`: include `not present in the publisher snapshot`
- `unsafe_filter`: include `publication filter omits subscriber columns`
- `primary_key_omitted`: include `publication filter omits primary key columns`
- `identity_filter_blocked`: include `REPLICA IDENTITY FULL`
