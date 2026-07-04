CREATE TABLE IF NOT EXISTS stations (
    station_key TEXT PRIMARY KEY,
    station_id INTEGER NOT NULL,
    mountpoint TEXT NOT NULL,
    last_sequence INTEGER NOT NULL,
    gap_count INTEGER NOT NULL DEFAULT 0,
    observable_sum REAL NOT NULL DEFAULT 0,
    last_epoch_ms INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS station_audit (
    event_id TEXT PRIMARY KEY,
    station_key TEXT NOT NULL,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
