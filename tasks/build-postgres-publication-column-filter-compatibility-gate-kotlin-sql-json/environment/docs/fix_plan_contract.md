The plan report has keys `summary` and `actions`. The summary contains `actions`, `blockingActions`, and `reviewActions`.

Actions are sorted by severity, subscription, publication, table, and type. Blocking actions sort before review actions. Action objects contain `type`, `severity`, `subscription`, `publication`, `table`, `columns`, `sql`, and `reason`. SQL-emitting actions use severity `blocking`; human-only actions use severity `review`.

`missing_table` diagnostics become `add_table_to_publication`. Their SQL uses bare identifiers and omits a column list, such as `ALTER PUBLICATION ops_pub ADD TABLE ops.events;`.

Column filter problems become `widen_column_filter` with the sorted union of already published columns and subscriber-needed columns that exist in the publisher schema. When `unsafe_filter` and `primary_key_omitted` both affect the same result, emit one widened-filter action that unions the missing columns from both diagnostics. Columns reported by `missing_column` are schema gaps and must not be added to widened filter SQL. Widening SQL uses bare identifiers and a deterministic column list, such as `ALTER PUBLICATION ops_pub SET TABLE ops.widgets (owner_id, widget_id);`.

`identity_filter_blocked` becomes `review_replica_identity`. `missing_column` becomes `review_schema_gap`. `missing_publication` becomes `create_publication_review`. Review actions must leave `sql` empty and use severity `review`; do not use `warning` for these actions. SQL actions must be deterministic, use unquoted/bare identifiers rather than double-quoted identifiers, and end with a semicolon.
