-- ============================================================
-- TELCO CUSTOMER 360 - MART VALIDATION
-- File: 14_create_pipeline_audit.sql
-- ============================================================

CREATE SCHEMA IF NOT EXISTS audit;

-- ============================================================
-- Table pipeline_run
-- ============================================================

CREATE TABLE IF NOT EXISTS audit.pipeline_run (
    run_id BIGSERIAL PRIMARY KEY,

    pipeline_name VARCHAR(100) NOT NULL,

    started_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    finished_at TIMESTAMP,

    status VARCHAR(20) NOT NULL,

    error_message TEXT
);

-- ============================================================
-- Table pipeline_step for individual steps
-- ============================================================

CREATE TABLE IF NOT EXISTS audit.pipeline_step (
    step_id BIGSERIAL PRIMARY KEY,

    run_id BIGINT NOT NULL,

    step_name VARCHAR(100) NOT NULL,

    started_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    finished_at TIMESTAMP,

    status VARCHAR(20) NOT NULL,

    rows_processed INTEGER,

    error_message TEXT,

    CONSTRAINT fk_pipeline_run
        FOREIGN KEY (run_id)
        REFERENCES audit.pipeline_run(run_id)
);