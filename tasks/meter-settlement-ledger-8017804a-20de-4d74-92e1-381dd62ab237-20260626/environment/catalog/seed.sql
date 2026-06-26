INSERT INTO meters VALUES
  ('MTR-1001', 'ACC-110', 'north', 1.015, '2025-12-01T00:00:00Z', NULL),
  ('MTR-1002', 'ACC-110', 'north', 0.982, '2025-12-01T00:00:00Z', NULL),
  ('MTR-2001', 'ACC-220', 'central', 1.044, '2026-01-01T00:00:00Z', '2026-03-10T00:00:00Z'),
  ('MTR-3001', 'ACC-330', 'south', 0.956, '2025-11-15T00:00:00Z', NULL),
  ('MTR-4001', 'ACC-440', 'west', 1.128, '2026-02-15T00:00:00Z', NULL),
  ('MTR-5001', 'ACC-550', 'east', 1.000, '2026-01-20T00:00:00Z', NULL);

INSERT INTO account_rates VALUES
  ('ACC-110', '2026-01', 18),
  ('ACC-110', '2026-03', 21),
  ('ACC-220', '2026-01', 22),
  ('ACC-330', '2026-01', 16),
  ('ACC-330', '2026-03', 17),
  ('ACC-440', '2026-01', 24),
  ('ACC-550', '2026-01', 19),
  ('ACC-550', '2026-03', 20);

INSERT INTO district_credits VALUES
  ('central', 3),
  ('east', 2),
  ('north', 2),
  ('south', 1),
  ('west', 4);

INSERT INTO district_billing_windows VALUES
  ('central', -6, 1, 4),
  ('east', -5, 3, 5),
  ('north', -5, 2, 6),
  ('south', -6, 1, 7),
  ('west', -8, 1, 8);

INSERT INTO district_peak_windows VALUES
  ('central', 4, 6),
  ('east', 3, 5),
  ('north', 20, 23),
  ('south', 22, 24),
  ('west', 12, 15);

INSERT INTO district_holidays VALUES
  ('central', '2026-02-17'),
  ('north', '2026-02-20'),
  ('west', '2026-03-18');

INSERT INTO district_rate_adjustments VALUES
  ('central', 'standard', 0),
  ('central', 'peak', 5),
  ('east', 'standard', 0),
  ('east', 'peak', 4),
  ('north', 'standard', 0),
  ('north', 'peak', 6),
  ('south', 'standard', 0),
  ('south', 'peak', 3),
  ('west', 'standard', 0),
  ('west', 'peak', 7);

INSERT INTO meter_register_baselines VALUES
  ('MTR-1001', '2026-02-20T00:00:00Z', 8100.000, 10000.000),
  ('MTR-4001', '2026-03-17T00:00:00Z', 9998.400, 10000.000);

INSERT INTO manual_adjustments VALUES
  ('ACC-220', '2026-02', 'central', -5, 'late-meter-dispute'),
  ('ACC-440', '2026-03', 'west', 12, 'distribution-true-up'),
  ('ACC-550', '2026-03', 'east', -4, 'manual-credit-review');
