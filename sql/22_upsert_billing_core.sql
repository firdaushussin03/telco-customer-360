-- ============================================================
-- TELCO CUSTOMER 360 - BILLING CORE UPSERT
-- File: 22_upsert_billing_core.sql
--
-- Purpose:
--   - Insert new bills into CORE
--   - Update existing bills when a newer version arrives
--   - Prevent duplicate bill_id records
--
-- Grain:
--   1 row = 1 current trusted bill
-- ============================================================


BEGIN;


INSERT INTO core.billing_transactions (

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
    transformed_at

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
    transformed_at

FROM staging.billing_transactions


ON CONFLICT (bill_id)

DO UPDATE SET

    customer_id = EXCLUDED.customer_id,

    billing_date = EXCLUDED.billing_date,

    base_monthly_charge =
        EXCLUDED.base_monthly_charge,

    long_distance_charge =
        EXCLUDED.long_distance_charge,

    extra_data_charge =
        EXCLUDED.extra_data_charge,

    discount_amount =
        EXCLUDED.discount_amount,

    total_amount =
        EXCLUDED.total_amount,

    payment_method =
        EXCLUDED.payment_method,

    payment_status =
        EXCLUDED.payment_status,

    created_at =
        EXCLUDED.created_at,

    updated_at =
        EXCLUDED.updated_at,

    source_file_name =
        EXCLUDED.source_file_name,

    ingested_at =
        EXCLUDED.ingested_at,

    transformed_at =
        EXCLUDED.transformed_at,

    core_updated_at =
        CURRENT_TIMESTAMP


-- Only update CORE if STAGING contains
-- a newer source version of the bill.
WHERE
    EXCLUDED.updated_at
        > core.billing_transactions.updated_at;


COMMIT;