CREATE TABLE IF NOT EXISTS cron_jobs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    job_class VARCHAR(255) NOT NULL,
    cron_expr VARCHAR(255) NOT NULL,
    zone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    misfire VARCHAR(64) NOT NULL DEFAULT 'FIRE_NOW',
    concurrent_execution_disallowed BOOLEAN NOT NULL DEFAULT FALSE,
    state VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    next_fire_time TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cron_jobs_state_next ON cron_jobs(state, next_fire_time);

CREATE TABLE IF NOT EXISTS cron_executions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    error_message VARCHAR(2000) NULL,
    last_heartbeat TIMESTAMP NULL,
    worker_id VARCHAR(128) NULL,
    recovery_attempt INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_cron_executions_job FOREIGN KEY (job_id) REFERENCES cron_jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_cron_executions_status ON cron_executions(status, scheduled_time);
CREATE INDEX IF NOT EXISTS idx_cron_executions_job_status ON cron_executions(job_id, status);
CREATE INDEX IF NOT EXISTS idx_cron_executions_heartbeat ON cron_executions(status, last_heartbeat);
