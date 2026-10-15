-- ============================================================
-- TELCO CUSTOMER 360 - BILLING STAGING TRANSFORMATION
-- File: 20_transform_billing_staging.sql
--
-- Purpose:
--   - Transform RAW billing data into a clean staging dataset
--   - Keep only the latest version of each bill_id
--   - Preserve lineage metadata
--
-- Grain:
--   1 row = 1 latest version of 1 bill
-- ============================================================


DROP TABLE IF EXISTS staging.billing_transactions;


CREATE TABLE staging.billing_transactions AS

WITH ranked_bills AS (

    SELECT
        bill_id,
        customer_id,
        billing_date,

        base_monthly_charge,
        long_distance_charge,
        extra_data_charge,
        discount_amount,
        total_amount,

        payment_method,
        payment_status,

        created_at,
        updated_at,

        source_file_name,
        ingested_at,

        ROW_NUMBER() OVER (
            PARTITION BY bill_id
            ORDER BY
                updated_at DESC,
                ingested_at DESC
        ) AS row_num

    FROM raw.billing_transactions
)

SELECT
    bill_id,
    customer_id,
    billing_date,

    base_monthly_charge,
    long_distance_charge,
    extra_data_charge,
    discount_amount,
    total_amount,

    payment_method,
    payment_status,

    created_at,
    updated_at,

    source_file_name,
    ingested_at,

    CURRENT_TIMESTAMP AS transformed_at

FROM ranked_bills

WHERE row_num = 1;