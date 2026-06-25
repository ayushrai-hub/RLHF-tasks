INSERT INTO meters VALUES
  ('MTR-1001', 'ACC-110', 'north', 1.015, '2025-12-01T00:00:00Z', NULL),
  ('MTR-1002', 'ACC-110', 'north', 0.982, '2025-12-01T00:00:00Z', NULL),
  ('MTR-2001', 'ACC-220', 'central', 1.044, '2026-01-01T00:00:00Z', '2026-03-10T00:00:00Z'),
  ('MTR-3001', 'ACC-330', 'south', 0.956, '2025-11-15T00:00:00Z', NULL),
  ('MTR-4001', 'ACC-440', 'west', 1.128, '2026-02-15T00:00:00Z', NULL),
  ('MTR-5001', 'ACC-550', 'east', 1.000, '2026-01-20T00:00:00Z', NULL);

INSERT INTO account_rates VALUES
  ('ACC-110', 18),
  ('ACC-220', 22),
  ('ACC-330', 16),
  ('ACC-440', 24),
  ('ACC-550', 19);

INSERT INTO district_credits VALUES
  ('central', 3),
  ('east', 2),
  ('north', 2),
  ('south', 1),
  ('west', 4);

INSERT INTO manual_adjustments VALUES
  ('ACC-220', '2026-02', 'central', -5, 'late-meter-dispute'),
  ('ACC-440', '2026-03', 'west', 12, 'distribution-true-up'),
  ('ACC-550', '2026-03', 'east', -4, 'manual-credit-review');
