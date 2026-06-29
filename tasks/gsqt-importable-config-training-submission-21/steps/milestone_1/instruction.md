The GSQT-style package in `/app` still opens production database connections during import. Make the core service modules importable with `GSQT_QUERY_DSN` and `GSQT_NODE_DSN` unset.

Keep `get_query_engine()` and `get_node_engine()` as the public runtime accessors, but make them lazy. If an accessor is called without its matching environment variable, raise a clear `RuntimeError` naming that variable. Keep `DatabaseOperations.update_by_id(connection, table, record_id, **fields)` working with an explicit SQLite connection.

Make the import-safety pass cover all current service modules: `src.config.database`, `src.query_scheduling.scheduler`, `src.steps.generator`, `src.user_service`, and `src.node_service`. When the DSN variables are configured, the lazy accessors should still return usable SQLite connections.

The accessor cache should follow the current DSN value: if `GSQT_QUERY_DSN` or `GSQT_NODE_DSN` changes after a connection was opened, the next accessor call should use the new DSN. SQLite `file:` URI DSNs such as `file:/tmp/query.sqlite?mode=rw` should be treated as SQLite URIs.

Do not paper over missing configuration with dummy global connections; later milestones will inject explicit fake databases.
