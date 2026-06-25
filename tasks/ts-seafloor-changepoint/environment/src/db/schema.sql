-- PSON sensor database schema
-- Populated with readings from January 2024

CREATE TABLE IF NOT EXISTS stations (
  code            TEXT PRIMARY KEY,
  full_name       TEXT NOT NULL,
  latitude        REAL NOT NULL,
  longitude       REAL NOT NULL,
  depth_m         REAL NOT NULL,
  deployment_date TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS readings (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  station_id  TEXT    NOT NULL,
  sensor_type TEXT    NOT NULL,  -- 'pressure', 'tilt_x', 'tilt_y', 'temperature'
  timestamp   TEXT    NOT NULL,  -- ISO 8601 UTC, e.g. '2024-01-15T04:00:00.000Z'
  raw_value   REAL    NOT NULL,
  unit        TEXT    NOT NULL,
  FOREIGN KEY (station_id) REFERENCES stations(code)
);

CREATE INDEX IF NOT EXISTS idx_readings_station_sensor_time
  ON readings (station_id, sensor_type, timestamp);
