-- ============================================================
-- TELCO CUSTOMER 360 - BILLING RAW TABLE
-- File: 17_create_billing_raw_table.sql
--
-- Grain:
--   1 source record = 1 billing record received
--
-- Purpose:
--   - Preserve billing source data
--   - Allow duplicate / updated bill versions to land
--   - Perform validation after ingestion
-- ============================================================

CREATE TABLE IF NOT EXISTS raw.billing_transactions (

    bill_id VARCHAR(30),
    customer_id VARCHAR(20),

    billing_date DATE,

    base_monthly_charge NUMERIC(12,2),
    long_distance_charge NUMERIC(12,2),
    extra_data_charge NUMERIC(12,2),
    discount_amount NUMERIC(12,2),
    total_amount NUMERIC(12,2),

    payment_method VARCHAR(50),
    payment_status VARCHAR(20),

    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    source_file_name VARCHAR(255),

    ingested_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
);

SELECT COUNT(*) FROM raw.billing_transactions;