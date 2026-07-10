CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    max_end_ms INTEGER NOT NULL,
    tree_left_id INTEGER REFERENCES events(id),
    tree_right_id INTEGER REFERENCES events(id),
    tree_parent_id INTEGER REFERENCES events(id),
    created_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS stab_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at_ms INTEGER NOT NULL,
    result_count INTEGER NOT NULL,
    duration_us INTEGER NOT NULL,
    ts_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS overlap_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    result_count INTEGER NOT NULL,
    duration_us INTEGER NOT NULL,
    ts_ms INTEGER NOT NULL
);
