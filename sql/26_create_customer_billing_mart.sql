-- ============================================================
-- TELCO CUSTOMER 360 - CUSTOMER BILLING SUMMARY MART
-- File: 26_create_customer_billing_mart.sql
--
-- Purpose:
--   - Aggregate transactional billing data to customer level
--   - Provide analytics-ready billing metrics
--
-- Grain:
--   1 row = 1 customer
-- ============================================================


DROP TABLE IF EXISTS mart.customer_billing_summary;


CREATE TABLE mart.customer_billing_summary AS

SELECT

    customer_id,

    COUNT(*) AS number_of_bills,

    SUM(total_amount) AS total_billed_amount,

    AVG(total_amount) AS average_bill_amount,

    SUM(discount_amount) AS total_discount_amount,

    SUM(long_distance_charge)
        AS total_long_distance_charge,

    SUM(extra_data_charge)
        AS total_extra_data_charge,

    COUNT(*) FILTER (
        WHERE payment_status = 'Paid'
    ) AS paid_bill_count,

    COUNT(*) FILTER (
        WHERE payment_status = 'Pending'
    ) AS pending_bill_count,

    COUNT(*) FILTER (
        WHERE payment_status = 'Failed'
    ) AS failed_bill_count,

    MIN(billing_date) AS first_billing_date,

    MAX(billing_date) AS latest_billing_date,

    CURRENT_TIMESTAMP AS mart_loaded_at

FROM core.billing_transactions

GROUP BY customer_id;