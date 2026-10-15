-- ============================================================
-- TELCO CUSTOMER 360 - ENRICHED CUSTOMER 360 VALIDATION
-- File: 29_validate_enriched_customer_360_mart.sql
--
-- Purpose:
--   - Validate the final enriched Customer 360 mart
--   - Confirm customer grain is preserved
--   - Confirm billing summary joined correctly
--   - Reconcile billing metrics
--
-- Grain:
--   1 row = 1 customer
-- ============================================================


-- ============================================================
-- 1. ROW COUNT
-- ============================================================

SELECT COUNT(*) AS enriched_customer_count
FROM mart.customer_360_enriched;


-- Expected:
-- 7043


-- ============================================================
-- 2. COMPARE CUSTOMER COUNTS
-- ============================================================

SELECT

    (
        SELECT COUNT(*)
        FROM core.customer
    ) AS core_customer_count,

    (
        SELECT COUNT(*)
        FROM mart.customer_360
    ) AS customer_360_count,

    (
        SELECT COUNT(*)
        FROM mart.customer_360_enriched
    ) AS enriched_customer_count;


-- Expected:
-- all = 7043


-- ============================================================
-- 3. DUPLICATE CUSTOMER IDs
-- ============================================================

SELECT
    customer_id,
    COUNT(*) AS duplicate_count

FROM mart.customer_360_enriched

GROUP BY customer_id

HAVING COUNT(*) > 1;


-- Expected:
-- 0 rows


-- ============================================================
-- 4. CORE CUSTOMERS MISSING FROM ENRICHED MART
-- ============================================================

SELECT COUNT(*) AS missing_customers
FROM core.customer c

LEFT JOIN mart.customer_360_enriched e
    ON c.customer_id = e.customer_id

WHERE e.customer_id IS NULL;


-- Expected:
-- 0


-- ============================================================
-- 5. CUSTOMERS WITHOUT BILLING
-- ============================================================

SELECT COUNT(*) AS customers_without_billing
FROM mart.customer_360_enriched

WHERE number_of_bills = 0;


-- Current expected:
-- 0


-- ============================================================
-- 6. PAYMENT COUNTS MUST EQUAL BILL COUNT
-- ============================================================

SELECT COUNT(*) AS invalid_payment_counts
FROM mart.customer_360_enriched

WHERE
    paid_bill_count
    + pending_bill_count
    + failed_bill_count
    <> number_of_bills;


-- Expected:
-- 0


-- ============================================================
-- 7. BILLING SUMMARY MUST MATCH ENRICHED MART
-- ============================================================

SELECT COUNT(*) AS billing_mismatch_rows

FROM mart.customer_360_enriched e

JOIN mart.customer_billing_summary b
    ON e.customer_id = b.customer_id

WHERE

       e.number_of_bills
            IS DISTINCT FROM b.number_of_bills

    OR e.total_billed_amount
            IS DISTINCT FROM b.total_billed_amount

    OR e.average_bill_amount
            IS DISTINCT FROM b.average_bill_amount

    OR e.total_discount_amount
            IS DISTINCT FROM b.total_discount_amount

    OR e.billing_long_distance_charge
            IS DISTINCT FROM b.total_long_distance_charge

    OR e.billing_extra_data_charge
            IS DISTINCT FROM b.total_extra_data_charge

    OR e.paid_bill_count
            IS DISTINCT FROM b.paid_bill_count

    OR e.pending_bill_count
            IS DISTINCT FROM b.pending_bill_count

    OR e.failed_bill_count
            IS DISTINCT FROM b.failed_bill_count

    OR e.first_billing_date
            IS DISTINCT FROM b.first_billing_date

    OR e.latest_billing_date
            IS DISTINCT FROM b.latest_billing_date;


-- Expected:
-- 0


-- ============================================================
-- 8. RECONCILE TOTAL NUMBER OF BILLS
-- ============================================================

SELECT

    (
        SELECT COUNT(*)
        FROM core.billing_transactions
    ) AS core_bill_count,

    (
        SELECT SUM(number_of_bills)
        FROM mart.customer_360_enriched
    ) AS enriched_bill_count;


-- Expected:
-- both = 42258


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
        FROM mart.customer_360_enriched
    ) AS enriched_total_billed;


-- Expected:
-- both totals should match


-- ============================================================
-- 10. INVALID BILLING VALUES
-- ============================================================

SELECT COUNT(*) AS invalid_billing_values
FROM mart.customer_360_enriched

WHERE
       number_of_bills < 0
    OR total_billed_amount < 0
    OR average_bill_amount < 0
    OR total_discount_amount < 0
    OR billing_long_distance_charge < 0
    OR billing_extra_data_charge < 0
    OR paid_bill_count < 0
    OR pending_bill_count < 0
    OR failed_bill_count < 0;


-- Expected:
-- 0


-- ============================================================
-- 11. INVALID BILLING DATE RANGE
-- ============================================================

SELECT COUNT(*) AS invalid_billing_dates
FROM mart.customer_360_enriched

WHERE first_billing_date > latest_billing_date;


-- Expected:
-- 0