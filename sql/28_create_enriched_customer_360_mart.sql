-- ============================================================
-- TELCO CUSTOMER 360 - ENRICHED CUSTOMER 360 MART
-- File: 28_create_enriched_customer_360_mart.sql
--
-- Purpose:
--   - Combine customer profile / service / churn information
--     with aggregated billing behaviour
--
-- Grain:
--   1 row = 1 customer
-- ============================================================


DROP TABLE IF EXISTS mart.customer_360_enriched;


CREATE TABLE mart.customer_360_enriched AS

SELECT

    c.*,

    -- ========================================================
    -- BILLING SUMMARY
    -- ========================================================

    COALESCE(
        b.number_of_bills,
        0
    ) AS number_of_bills,

    COALESCE(
        b.total_billed_amount,
        0
    ) AS total_billed_amount,

    COALESCE(
        b.average_bill_amount,
        0
    ) AS average_bill_amount,

    COALESCE(
        b.total_discount_amount,
        0
    ) AS total_discount_amount,

    COALESCE(
        b.total_long_distance_charge,
        0
    ) AS billing_long_distance_charge,

    COALESCE(
        b.total_extra_data_charge,
        0
    ) AS billing_extra_data_charge,

    COALESCE(
        b.paid_bill_count,
        0
    ) AS paid_bill_count,

    COALESCE(
        b.pending_bill_count,
        0
    ) AS pending_bill_count,

    COALESCE(
        b.failed_bill_count,
        0
    ) AS failed_bill_count,

    b.first_billing_date,

    b.latest_billing_date,

    CURRENT_TIMESTAMP AS enriched_mart_loaded_at

FROM mart.customer_360 c

LEFT JOIN mart.customer_billing_summary b
    ON c.customer_id = b.customer_id;