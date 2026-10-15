-- ============================================================
-- TELCO CUSTOMER 360 - PIPELINE WATERMARK
-- File: 18_create_pipeline_watermark.sql
--
-- Purpose:
--   - Track the latest successfully processed source timestamp
--   - Support incremental data loading
-- ============================================================


CREATE TABLE IF NOT EXISTS audit.pipeline_watermark (

    pipeline_name VARCHAR(100) NOT NULL,
    source_name VARCHAR(100) NOT NULL,

    last_watermark TIMESTAMP NOT NULL,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        pipeline_name,
        source_name
    )
);


-- ============================================================
-- INITIAL WATERMARK FOR BILLING
-- ============================================================

INSERT INTO audit.pipeline_watermark (
    pipeline_name,
    source_name,
    last_watermark
)
VALUES (
    'telco_customer_360',
    'billing_transactions',
    '1900-01-01 00:00:00'
)

ON CONFLICT (
    pipeline_name,
    source_name
)
DO NOTHING;