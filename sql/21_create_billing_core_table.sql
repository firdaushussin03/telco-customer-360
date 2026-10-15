-- ============================================================
-- TELCO CUSTOMER 360 - BILLING CORE TABLE
-- File: 21_create_billing_core_table.sql
--
-- Purpose:
--   - Store the trusted current version of each bill
--   - Enforce data quality and relationships
--   - Support incremental UPSERT loading
--
-- Grain:
--   1 row = 1 current trusted bill
-- ============================================================


CREATE TABLE IF NOT EXISTS core.billing_transactions (

    bill_id VARCHAR(30) PRIMARY KEY,

    customer_id VARCHAR(20) NOT NULL,

    billing_date DATE NOT NULL,

    base_monthly_charge NUMERIC(12,2) NOT NULL
        CHECK (base_monthly_charge >= 0),

    long_distance_charge NUMERIC(12,2) NOT NULL
        CHECK (long_distance_charge >= 0),

    extra_data_charge NUMERIC(12,2) NOT NULL
        CHECK (extra_data_charge >= 0),

    discount_amount NUMERIC(12,2) NOT NULL
        CHECK (discount_amount >= 0),

    total_amount NUMERIC(12,2) NOT NULL
        CHECK (total_amount >= 0),

    payment_method VARCHAR(50) NOT NULL,

    payment_status VARCHAR(20) NOT NULL
        CHECK (
            payment_status IN (
                'Paid',
                'Pending',
                'Failed'
            )
        ),

    created_at TIMESTAMP NOT NULL,

    updated_at TIMESTAMP NOT NULL,

    source_file_name VARCHAR(255) NOT NULL,

    ingested_at TIMESTAMP NOT NULL,

    transformed_at TIMESTAMP NOT NULL,

    core_loaded_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    core_updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,


    CONSTRAINT fk_billing_customer
        FOREIGN KEY (customer_id)
        REFERENCES core.customer(customer_id),


    CONSTRAINT chk_billing_update_time
        CHECK (updated_at >= created_at)
);