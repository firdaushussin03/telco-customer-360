-- ============================================================
-- TELCO CUSTOMER 360 - CUSTOMER BILLING MART VALIDATION
-- File: 27_validate_customer_billing_mart.sql
--
-- Purpose:
--   - Validate customer-level billing aggregation
--   - Confirm mart grain
--   - Reconcile mart totals with CORE billing
--
-- Grain:
--   1 row = 1 customer
-- ============================================================


-- ============================================================
-- 1. ROW COUNT
-- ============================================================

SELECT COUNT(*) AS billing_mart_rows
FROM mart.customer_billing_summary;


-- Expected:
-- 7043


-- ============================================================
-- 2. DUPLICATE CUSTOMER IDs
-- ============================================================

SELECT
    customer_id,
    COUNT(*) AS duplicate_count
FROM mart.customer_billing_summary
GROUP BY customer_id
HAVING COUNT(*) > 1;


-- Expected:
-- 0 rows


-- ============================================================
-- 3. CORE CUSTOMERS MISSING FROM BILLING MART
-- ============================================================

SELECT COUNT(*) AS customers_missing_from_billing_mart
FROM core.customer c

LEFT JOIN mart.customer_billing_summary b
    ON c.customer_id = b.customer_id

WHERE b.customer_id IS NULL;


-- Expected:
-- 0


-- ============================================================
-- 4. TOTAL NUMBER OF BILLS
-- ============================================================

SELECT
    SUM(number_of_bills) AS mart_bill_count
FROM mart.customer_billing_summary;


-- Expected:
-- 42258


-- ============================================================
-- 5. COMPARE MART BILL COUNT WITH CORE
-- ============================================================

SELECT

    (
        SELECT COUNT(*)
        FROM core.billing_transactions
    ) AS core_bill_count,

    (
        SELECT SUM(number_of_bills)
        FROM mart.customer_billing_summary
    ) AS mart_bill_count;


-- Expected:
-- both = 42258


-- ============================================================
-- 6. PAYMENT COUNTS MUST EQUAL NUMBER OF BILLS
-- ============================================================

SELECT COUNT(*) AS invalid_payment_count_rows
FROM mart.customer_billing_summary

WHERE
    paid_bill_count
    + pending_bill_count
    + failed_bill_count
    <> number_of_bills;


-- Expected:
-- 0


-- ============================================================
-- 7. INVALID NEGATIVE VALUES
-- ============================================================

SELECT COUNT(*) AS invalid_negative_values
FROM mart.customer_billing_summary

WHERE
       total_billed_amount < 0
    OR average_bill_amount < 0
    OR total_discount_amount < 0
    OR total_long_distance_charge < 0
    OR total_extra_data_charge < 0;


-- Expected:
-- 0


-- ============================================================
-- 8. DATE RANGE VALIDATION
-- ============================================================

SELECT COUNT(*) AS invalid_date_ranges
FROM mart.customer_billing_summary

WHERE first_billing_date > latest_billing_date;


-- Expected:
-- 0


-- ============================================================
-- 9. RECONCILE TOTAL BILLED AMOUNT
-- ============================================================

SELECT

    (
        SELECT SUM(total_amount)
        FROM core.billing_transactions
    ) AS core_total_billed,

    (
        SELECT SUM(total_billed_amount)
        FROM mart.customer_billing_summary
    ) AS mart_total_billed;


-- Expected:
-- both totals should match


-- ============================================================
-- 10. BILL COUNT DISTRIBUTION
-- ============================================================

SELECT
    number_of_bills,
    COUNT(*) AS customer_count
FROM mart.customer_billing_summary
GROUP BY number_of_bills	
ORDER BY number_of_bills;


-- Current expected result:
--
-- number_of_bills | customer_count
-- ----------------+---------------
-- 6               | 7043