CREATE TABLE IF NOT EXISTS room_aliases (
  alias TEXT PRIMARY KEY,
  canonical TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rooms (
  room_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS room_exits (
  from_room TEXT NOT NULL,
  direction TEXT NOT NULL,
  to_room TEXT NOT NULL,
  requires_key INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (from_room, direction)
);

CREATE TABLE IF NOT EXISTS room_clues (
  room_id TEXT PRIMARY KEY,
  clue_blob TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS puzzle_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  current_room TEXT NOT NULL,
  has_key INTEGER NOT NULL DEFAULT 0,
  final_score INTEGER NOT NULL DEFAULT 0,
  rooms_visited TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS move_log (
  seq INTEGER PRIMARY KEY,
  move_text TEXT NOT NULL
);
DELETE FROM room_aliases;
DELETE FROM rooms;
DELETE FROM room_exits;
DELETE FROM room_clues;
DELETE FROM puzzle_state;
DELETE FROM move_log;
INSERT INTO room_aliases(alias, canonical) VALUES('foyer', 'entry');
INSERT INTO room_aliases(alias, canonical) VALUES('antechamber', 'hall');
INSERT INTO room_aliases(alias, canonical) VALUES('stacks', 'library');
INSERT INTO rooms(room_id, display_name) VALUES('entry', 'ENTRY');
INSERT INTO rooms(room_id, display_name) VALUES('hall', 'HALL');
INSERT INTO rooms(room_id, display_name) VALUES('library', 'LIBRARY');
INSERT INTO rooms(room_id, display_name) VALUES('garden', 'GARDEN');
INSERT INTO rooms(room_id, display_name) VALUES('crypt', 'CRYPT');
INSERT INTO rooms(room_id, display_name) VALUES('vault', 'VAULT');
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('entry', 'east', 'hall', 0);
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('hall', 'west', 'entry', 0);
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('hall', 'north', 'library', 0);
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('library', 'south', 'hall', 0);
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('library', 'east', 'garden', 0);
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('garden', 'west', 'library', 0);
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('garden', 'north', 'crypt', 0);
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('crypt', 'south', 'garden', 0);
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('crypt', 'east', 'vault', 1);
INSERT INTO room_exits(from_room, direction, to_room, requires_key) VALUES('vault', 'south', 'crypt', 0);
INSERT INTO room_clues(room_id, clue_blob) VALUES('entry', 'eyJhdGxhc19jb2wiOjEsImF0bGFzX3JvdyI6MSwiZ2x5cGhfaWQiOiJlbnRyeSIsImhpbnRfd2VpZ2h0IjoyfQ==');
INSERT INTO room_clues(room_id, clue_blob) VALUES('hall', 'eyJhdGxhc19jb2wiOjIsImF0bGFzX3JvdyI6MSwiZ2x5cGhfaWQiOiJoYWxsIiwiaGludF93ZWlnaHQiOjN9');
INSERT INTO room_clues(room_id, clue_blob) VALUES('library', 'eyJhdGxhc19jb2wiOjMsImF0bGFzX3JvdyI6MSwiZ2x5cGhfaWQiOiJsaWJyYXJ5IiwiaGludF93ZWlnaHQiOjR9');
INSERT INTO room_clues(room_id, clue_blob) VALUES('garden', 'eyJhdGxhc19jb2wiOjEsImF0bGFzX3JvdyI6MiwiZ2x5cGhfaWQiOiJnYXJkZW4iLCJoaW50X3dlaWdodCI6M30=');
INSERT INTO room_clues(room_id, clue_blob) VALUES('crypt', 'eyJhdGxhc19jb2wiOjIsImF0bGFzX3JvdyI6MiwiZ2x5cGhfaWQiOiJjcnlwdCIsImhpbnRfd2VpZ2h0Ijo1fQ==');
INSERT INTO room_clues(room_id, clue_blob) VALUES('vault', 'eyJhdGxhc19jb2wiOjMsImF0bGFzX3JvdyI6MiwiZ2x5cGhfaWQiOiJ2YXVsdCIsImhpbnRfd2VpZ2h0Ijo3fQ==');
INSERT INTO puzzle_state(id, current_room, has_key, final_score, rooms_visited) VALUES(1, 'entry', 0, 0, '[]');
