PRAGMA foreign_keys = ON;

CREATE TABLE sweeps (
    sweep_id TEXT PRIMARY KEY,
    kernel_revision TEXT NOT NULL,
    dt REAL NOT NULL,
    dimension INTEGER NOT NULL,
    fit_lag_min INTEGER NOT NULL DEFAULT 2,
    fit_lag_max INTEGER NOT NULL DEFAULT 5
);

CREATE TABLE msd_points (
    sweep_id TEXT NOT NULL,
    lag_step INTEGER NOT NULL,
    msd REAL NOT NULL,
    PRIMARY KEY (sweep_id, lag_step),
    FOREIGN KEY (sweep_id) REFERENCES sweeps (sweep_id)
);

CREATE TABLE diffusion_summary (
    sweep_id TEXT PRIMARY KEY,
    kernel_revision TEXT NOT NULL,
    diffusion_coeff REAL NOT NULL,
    rss REAL NOT NULL,
    FOREIGN KEY (sweep_id) REFERENCES sweeps (sweep_id)
);
