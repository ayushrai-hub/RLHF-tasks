PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS goldsmiths (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL UNIQUE,
  rank       TEXT NOT NULL CHECK (rank IN ('apprentice','journeyman','master')),
  specialty  TEXT NOT NULL CHECK (specialty IN ('ring','chalice','reliquary','crown','brooch')),
  mentor_id  INTEGER REFERENCES goldsmiths(id),
  joined_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crucibles (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  label            TEXT NOT NULL UNIQUE,
  capacity_g       REAL NOT NULL CHECK (capacity_g > 0),
  permitted_alloys TEXT NOT NULL DEFAULT '["14K","18K","22K","24K"]'  -- JSON array of allowed alloy_grade values
);

CREATE TABLE IF NOT EXISTS pieces (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  serial               TEXT NOT NULL UNIQUE,
  intent_kind          TEXT NOT NULL CHECK (intent_kind IN ('ring','chalice','reliquary','crown','brooch')),
  alloy_grade          TEXT NOT NULL CHECK (alloy_grade IN ('14K','18K','22K','24K')),
  target_mass_g        REAL NOT NULL CHECK (target_mass_g > 0),
  stage                TEXT NOT NULL DEFAULT 'ingot_selected'
                                CHECK (stage IN ('ingot_selected','assayed','cast_active',
                                                 'cast_complete','chased','hallmarked','released')),
  assigned_goldsmith   INTEGER REFERENCES goldsmiths(id),
  parent_id            INTEGER REFERENCES pieces(id),
  released_at          TEXT
);

CREATE TABLE IF NOT EXISTS piece_components (
  piece_id        INTEGER NOT NULL REFERENCES pieces(id),
  source_piece_id INTEGER NOT NULL REFERENCES pieces(id),
  fraction        REAL NOT NULL CHECK (fraction > 0 AND fraction <= 1),
  PRIMARY KEY (piece_id, source_piece_id)
);

CREATE TABLE IF NOT EXISTS castings (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  piece_id       INTEGER NOT NULL REFERENCES pieces(id),
  crucible_id    INTEGER NOT NULL REFERENCES crucibles(id),
  goldsmith_id   INTEGER NOT NULL REFERENCES goldsmiths(id),
  poured_mass_g  REAL NOT NULL CHECK (poured_mass_g > 0),
  starts_at      TEXT NOT NULL,
  ends_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assays (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  piece_id            INTEGER NOT NULL REFERENCES pieces(id),
  goldsmith_id        INTEGER NOT NULL REFERENCES goldsmiths(id),
  fineness_per_mille  INTEGER NOT NULL CHECK (fineness_per_mille >= 0 AND fineness_per_mille <= 1000),
  performed_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hallmarks (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  piece_id      INTEGER NOT NULL REFERENCES pieces(id),
  goldsmith_id  INTEGER NOT NULL REFERENCES goldsmiths(id),
  letter        TEXT NOT NULL CHECK (letter IN ('A','B','C','F')),
  notes         TEXT,
  recorded_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_entries (
  seq          INTEGER PRIMARY KEY AUTOINCREMENT,
  action       TEXT NOT NULL,
  payload      TEXT NOT NULL,
  prev_hash    TEXT NOT NULL,
  entry_hash   TEXT NOT NULL,
  occurred_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pieces_assigned   ON pieces(assigned_goldsmith);
CREATE INDEX IF NOT EXISTS idx_castings_crucible ON castings(crucible_id);
CREATE INDEX IF NOT EXISTS idx_castings_smith    ON castings(goldsmith_id);
CREATE INDEX IF NOT EXISTS idx_assays_piece      ON assays(piece_id);
CREATE INDEX IF NOT EXISTS idx_hallmarks_piece   ON hallmarks(piece_id);
CREATE INDEX IF NOT EXISTS idx_hallmarks_smith   ON hallmarks(goldsmith_id);
