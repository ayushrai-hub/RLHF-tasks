PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS meters;
DROP TABLE IF EXISTS account_rates;
DROP TABLE IF EXISTS district_credits;
DROP TABLE IF EXISTS district_billing_windows;
DROP TABLE IF EXISTS district_peak_windows;
DROP TABLE IF EXISTS district_holidays;
DROP TABLE IF EXISTS district_rate_adjustments;
DROP TABLE IF EXISTS meter_register_baselines;
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
  account_id TEXT NOT NULL,
  effective_month TEXT NOT NULL,
  rate_cents_per_kwh INTEGER NOT NULL,
  PRIMARY KEY (account_id, effective_month)
);

CREATE TABLE district_credits (
  district TEXT PRIMARY KEY,
  credit_cents_per_kwh INTEGER NOT NULL
);

CREATE TABLE district_billing_windows (
  district TEXT PRIMARY KEY,
  utc_offset_hours INTEGER NOT NULL,
  cutover_day INTEGER NOT NULL,
  cutover_hour INTEGER NOT NULL
);

CREATE TABLE district_peak_windows (
  district TEXT PRIMARY KEY,
  peak_start_hour INTEGER NOT NULL,
  peak_end_hour INTEGER NOT NULL
);

CREATE TABLE district_holidays (
  district TEXT NOT NULL,
  local_date TEXT NOT NULL,
  PRIMARY KEY (district, local_date)
);

CREATE TABLE district_rate_adjustments (
  district TEXT NOT NULL,
  billing_band TEXT NOT NULL,
  adjustment_cents_per_kwh INTEGER NOT NULL,
  PRIMARY KEY (district, billing_band)
);

CREATE TABLE meter_register_baselines (
  meter_id TEXT PRIMARY KEY,
  baseline_observed_at TEXT NOT NULL,
  baseline_register_kwh REAL NOT NULL,
  rollover_kwh REAL NOT NULL
);

CREATE TABLE manual_adjustments (
  account_id TEXT NOT NULL,
  service_month TEXT NOT NULL,
  district TEXT NOT NULL,
  adjustment_cents INTEGER NOT NULL,
  reason TEXT NOT NULL,
  PRIMARY KEY (account_id, service_month, district)
);
