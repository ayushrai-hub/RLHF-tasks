-- Goldsmiths: 3 mentor trees + 1 isolated.
--   albrecht (master ring)  → beatrix (journeyman chalice) → delphine (apprentice reliquary)
--                            → cassius  (journeyman crown)
--   ewald    (master brooch) → frieda  (apprentice ring)
--   gerold   (master ring)    -- isolated
--   hilde    (journeyman chalice) -- isolated
INSERT INTO goldsmiths (id, name, rank, specialty, mentor_id, joined_at) VALUES
  (1, 'albrecht',  'master',     'ring',       NULL, '2018-04-10T09:00:00Z'),
  (2, 'beatrix',   'journeyman', 'chalice',    1,    '2020-05-12T09:00:00Z'),
  (3, 'cassius',   'journeyman', 'crown',      1,    '2020-06-15T09:00:00Z'),
  (4, 'delphine',  'apprentice', 'reliquary',  2,    '2023-09-01T09:00:00Z'),
  (5, 'ewald',     'master',     'brooch',     NULL, '2017-03-22T09:00:00Z'),
  (6, 'frieda',    'apprentice', 'ring',       5,    '2024-01-20T09:00:00Z'),
  (7, 'gerold',    'master',     'ring',       NULL, '2019-11-05T09:00:00Z'),
  (8, 'hilde',     'journeyman', 'chalice',    NULL, '2021-07-30T09:00:00Z');

-- Crucibles.  permitted_alloys is a JSON array of alloy_grade strings that
-- the crucible is permitted to pour. Small crucible only does low-karat work;
-- large crucible does everything. See the crucible booking notes for the rule.
INSERT INTO crucibles (id, label, capacity_g, permitted_alloys) VALUES
  (1, 'AC-S1',  200.0, '["14K","18K"]'),
  (2, 'AC-M1',  500.0, '["14K","18K","22K"]'),
  (3, 'AC-L1', 1500.0, '["14K","18K","22K","24K"]');

-- Pieces.  Stage column drives the state-machine tests.
-- Lineage chain: 8 (root) ← 9 ← 10. Cycle: 17 ↔ 18.
PRAGMA foreign_keys = OFF;

INSERT INTO pieces (id, serial, intent_kind, alloy_grade, target_mass_g, stage, assigned_goldsmith, parent_id, released_at) VALUES
  (1,  'AA-0001', 'ring',      '24K',   50.0, 'released',       1,    NULL, '2025-10-10T16:00:00Z'),
  (2,  'AA-0002', 'chalice',   '22K',  300.0, 'released',       2,    NULL, '2025-11-02T16:00:00Z'),
  (3,  'AA-0003', 'brooch',    '22K',   20.0, 'hallmarked',     1,    NULL, NULL),
  (4,  'AA-0004', 'ring',      '18K',   18.0, 'released',       1,    NULL, '2025-11-20T16:00:00Z'),
  (5,  'AA-0005', 'crown',     '24K',  400.0, 'cast_complete',  3,    NULL, NULL),
  (6,  'AA-0006', 'reliquary', '18K',  150.0, 'chased',         4,    NULL, NULL),
  (7,  'AA-0007', 'ring',      '22K',   22.0, 'hallmarked',     1,    NULL, NULL),
  (8,  'AA-0008', 'brooch',    '22K',   15.0, 'hallmarked',     5,    NULL, NULL),
  (9,  'AA-0009', 'brooch',    '22K',   15.0, 'released',       5,    8,    '2025-12-15T16:00:00Z'),
  (10, 'AA-0010', 'brooch',    '22K',   12.0, 'cast_complete',  6,    9,    NULL),
  (11, 'AA-0011', 'ring',      '18K',   15.0, 'ingot_selected', NULL, NULL, NULL),
  (12, 'AA-0012', 'chalice',   '22K',  300.0, 'assayed',        2,    NULL, NULL),
  (13, 'AA-0013', 'ring',      '22K',   18.0, 'chased',         1,    NULL, NULL),
  (14, 'AA-0014', 'ring',      '22K',   22.0, 'chased',         1,    NULL, NULL),
  (15, 'AA-0015', 'ring',      '22K',   22.0, 'chased',         1,    NULL, NULL),
  (16, 'AA-0016', 'ring',      '22K',   22.0, 'chased',         1,    NULL, NULL),
  (17, 'AA-0017', 'chalice',   '18K',  100.0, 'ingot_selected', 2,    18,   NULL),
  (18, 'AA-0018', 'chalice',   '18K',  100.0, 'ingot_selected', 2,    17,   NULL),
  (19, 'AA-0019', 'ring',      '24K',   30.0, 'cast_active',    3,    NULL, NULL),
  (20, 'AA-0020', 'chalice',   '22K',  400.0, 'released',       7,    NULL, '2026-03-10T16:00:00Z');

PRAGMA foreign_keys = ON;

-- DAG provenance.  Two cases:
--   * piece 12 is a recast composite of pieces 1 (0.7) and 4 (0.3) — single hop.
--   * piece 20 is a deeper composite of piece 12 (0.5) and piece 8 (0.5) — two hops via 12.
INSERT INTO piece_components (piece_id, source_piece_id, fraction) VALUES
  (12, 1,  0.7),
  (12, 4,  0.3),
  (20, 12, 0.5),
  (20, 8,  0.5);

-- Castings.  Crucible-alloy matrix MUST hold:
--   crucible 1 ('AC-S1', 200g) permits 14K/18K only
--   crucible 2 ('AC-M1', 500g) permits 14K/18K/22K
--   crucible 3 ('AC-L1', 1500g) permits everything
-- Piece 19 has a casting that already ended → advance-stage can move it.
INSERT INTO castings (id, piece_id, crucible_id, goldsmith_id, poured_mass_g, starts_at, ends_at) VALUES
  (1, 5,  3, 3, 400.0, '2025-11-15T08:00:00Z', '2025-11-15T10:00:00Z'),
  (2, 6,  2, 4, 150.0, '2025-12-02T08:00:00Z', '2025-12-02T11:00:00Z'),
  (3, 10, 2, 6,  12.0, '2025-12-05T08:00:00Z', '2025-12-05T09:00:00Z'),
  (4, 19, 3, 3,  30.0, '2026-01-10T08:00:00Z', '2026-01-10T09:00:00Z');

-- Assays.  Piece 7 has five monthly assays for the trend test.
INSERT INTO assays (id, piece_id, goldsmith_id, fineness_per_mille, performed_at) VALUES
  (1,  1,  1, 999, '2025-10-05T10:00:00Z'),
  (2,  2,  2, 916, '2025-10-25T10:00:00Z'),
  (3,  3,  1, 916, '2025-12-10T10:00:00Z'),
  (4,  4,  1, 750, '2025-11-15T10:00:00Z'),
  (5,  5,  3, 999, '2025-11-14T10:00:00Z'),
  (6,  6,  4, 750, '2025-11-25T10:00:00Z'),
  (7,  7,  1, 900, '2025-08-15T10:00:00Z'),
  (8,  7,  1, 905, '2025-09-15T10:00:00Z'),
  (9,  7,  1, 915, '2025-10-15T10:00:00Z'),
  (10, 7,  1, 925, '2025-11-15T10:00:00Z'),
  (11, 7,  1, 930, '2025-12-15T10:00:00Z'),
  (12, 8,  5, 916, '2025-08-30T10:00:00Z'),
  (13, 9,  5, 916, '2025-11-10T10:00:00Z'),
  (14, 10, 6, 916, '2025-12-05T10:00:00Z'),
  (15, 12, 2, 916, '2026-01-05T10:00:00Z'),
  (16, 13, 1, 916, '2026-01-20T10:00:00Z'),
  (17, 14, 1, 916, '2026-01-20T10:00:00Z'),
  (18, 15, 1, 916, '2026-01-20T10:00:00Z'),
  (19, 16, 1, 916, '2026-01-20T10:00:00Z'),
  (20, 19, 3, 999, '2026-01-09T10:00:00Z'),
  (21, 20, 7, 916, '2026-02-15T10:00:00Z');

-- Hallmarks.  Smith 1's last 3 are all letter A → streak qualifies on workload.
-- Ordering matters: per the monotonic-timestamp rule, any new hallmark by a
-- given goldsmith must have recorded_at strictly greater than that goldsmith's
-- prior maximum.  The seed rows are pre-sorted per goldsmith.
INSERT INTO hallmarks (id, piece_id, goldsmith_id, letter, notes, recorded_at) VALUES
  (1, 1, 1, 'A', 'first inspection',  '2025-10-08T10:00:00Z'),
  (2, 4, 1, 'A', 'flawless',          '2025-11-18T10:00:00Z'),
  (3, 3, 1, 'A', 'crisp solder line', '2026-01-15T10:00:00Z'),
  (4, 7, 1, 'A', 'master grade ring', '2026-02-01T10:00:00Z'),
  (5, 2, 2, 'B', 'minor surface mark','2025-10-30T10:00:00Z'),
  (6, 8, 5, 'A', 'excellent finish',  '2025-09-02T10:00:00Z'),
  (7, 9, 5, 'B', 'small tool mark',   '2025-12-10T10:00:00Z'),
  (8, 20, 7, 'A', 'composite chalice', '2026-03-01T10:00:00Z');
