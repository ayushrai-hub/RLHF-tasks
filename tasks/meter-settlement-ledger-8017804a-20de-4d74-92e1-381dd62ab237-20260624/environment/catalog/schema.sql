PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS meters;
DROP TABLE IF EXISTS account_rates;
DROP TABLE IF EXISTS district_credits;
DROP TABLE IF EXISTS manual_adjustments;

CREATE TABLE meters (
  meter_id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  district TEXT NOT NULL,
  multiplier REAL NOT NULL,
  active_from TEXT NOT NULL,
  active_to TEXT
);

CREATE TABLE account_rates (
  account_id TEXT PRIMARY KEY,
  rate_cents_per_kwh INTEGER NOT NULL
);

CREATE TABLE district_credits (
  district TEXT PRIMARY KEY,
  credit_cents_per_kwh INTEGER NOT NULL
);

CREATE TABLE manual_adjustments (
  account_id TEXT NOT NULL,
  service_month TEXT NOT NULL,
  district TEXT NOT NULL,
  adjustment_cents INTEGER NOT NULL,
  reason TEXT NOT NULL,
  PRIMARY KEY (account_id, service_month, district)
);
