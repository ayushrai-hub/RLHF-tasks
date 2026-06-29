The parser emits a JSON snapshot with keys in this order: `tables`, `publications`, `subscriptions`.

Tables are sorted by schema then name. Table objects contain `schema`, `name`, `columns`, and `replicaIdentity`. Column objects contain `name`, `type`, `nullable`, and `primaryKey`, sorted by column name in parser output. Inline `PRIMARY KEY` and table-level `PRIMARY KEY (...)` constraints both set `primaryKey`; primary key columns are not nullable. Data types with modifiers, such as `numeric(12,2)`, are preserved as a single type string. `ALTER TABLE ... REPLICA IDENTITY FULL` sets `replicaIdentity` to `full`; otherwise it is `default`.

Publications are sorted by name. Publication objects contain `name` and `tables`. Each table reference contains `schema`, `name`, and `columns`. An empty `columns` array means the publication sends all columns for that table.

Subscriptions are sorted by name. Subscription objects contain `name`, `publication`, and `targetTables`. Each target table contains `schema`, `name`, and `columns`, where `columns` is the subscriber's expected receive set.

Snapshot JSON files are pretty printed with a trailing newline. The SQLite `columns_json` fields in `publication_tables` and `subscription_tables` store compact JSON arrays without spaces.
