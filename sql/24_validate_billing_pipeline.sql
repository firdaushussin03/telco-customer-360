-- ============================================================
-- TELCO CUSTOMER 360 - BILLING PIPELINE VALIDATION
-- File: 24_validate_billing_pipeline.sql
--
-- Purpose:
--   - Validate RAW, STAGING, and CORE billing layers
--   - Confirm latest bill versions are preserved correctly
--   - Confirm CORE contains trusted billing records
-- ============================================================


-- ============================================================
-- 1. ROW COUNTS
-- ============================================================

SELECT
    (SELECT COUNT(*)
     FROM raw.billing_transactions) AS raw_rows,

    (SELECT COUNT(*)
     FROM staging.billing_transactions) AS staging_rows,

    (SELECT COUNT(*)
     FROM core.billing_transactions) AS core_rows;


-- ============================================================
-- 2. RAW DISTINCT BILL COUNT
-- ============================================================

SELECT
    COUNT(DISTINCT bill_id) AS raw_unique_bills
FROM raw.billing_transactions;


-- Expected:
-- raw_unique_bills = staging row count


-- ============================================================
-- 3. DUPLICATE BILL IDs IN STAGING
-- ============================================================

SELECT
    bill_id,
    COUNT(*) AS duplicate_count
FROM staging.billing_transactions
GROUP BY bill_id
HAVING COUNT(*) > 1;


-- Expected:
-- 0 rows


-- ============================================================
-- 4. DUPLICATE BILL IDs IN CORE
-- ============================================================

SELECT
    bill_id,
    COUNT(*) AS duplicate_count
FROM core.billing_transactions
GROUP BY bill_id
HAVING COUNT(*) > 1;


-- Expected:
-- 0 rows


-- ============================================================
-- 5. STAGING MUST CONTAIN LATEST RAW VERSION
-- ============================================================

SELECT COUNT(*) AS outdated_staging_rows
FROM staging.billing_transactions s

WHERE EXISTS (

    SELECT 1

    FROM raw.billing_transactions r

    WHERE r.bill_id = s.bill_id

      AND r.updated_at > s.updated_at
);


-- Expected:
-- 0


-- ============================================================
-- 6. CORE MUST MATCH LATEST STAGING VERSION
-- ============================================================

SELECT COUNT(*) AS outdated_core_rows
FROM core.billing_transactions c

JOIN staging.billing_transactions s
    ON c.bill_id = s.bill_id

WHERE c.updated_at < s.updated_at;


-- Expected:
-- 0


-- ============================================================
-- 7. CHECK FOR MISSING CORE BILLS
-- ============================================================

SELECT COUNT(*) AS missing_core_bills
FROM staging.billing_transactions s

LEFT JOIN core.billing_transactions c
    ON s.bill_id = c.bill_id

WHERE c.bill_id IS NULL;


-- Expected:
-- 0


-- ============================================================
-- 8. CUSTOMER REFERENTIAL INTEGRITY
-- ============================================================

SELECT COUNT(*) AS orphan_billing_customers
FROM core.billing_transactions b

LEFT JOIN core.customer c
    ON b.customer_id = c.customer_id

WHERE c.customer_id IS NULL;


-- Expected:
-- 0


-- ============================================================
-- 9. INVALID PAYMENT STATUS
-- ============================================================

SELECT COUNT(*) AS invalid_payment_status
FROM core.billing_transactions

WHERE payment_status NOT IN (
    'Paid',
    'Pending',
    'Failed'
);


-- Expected:
-- 0


-- ============================================================
-- 10. INVALID NEGATIVE AMOUNTS
-- ============================================================

SELECT COUNT(*) AS invalid_negative_amounts
FROM core.billing_transactions

WHERE
       base_monthly_charge < 0
    OR long_distance_charge < 0
    OR extra_data_charge < 0
    OR discount_amount < 0
    OR total_amount < 0;


-- Expected:
-- 0


-- ============================================================
-- 11. INVALID SOURCE TIMESTAMPS
-- ============================================================

SELECT COUNT(*) AS invalid_timestamp_rows
FROM core.billing_transactions

WHERE updated_at < created_at;


-- Expected:
-- 0


-- ============================================================
-- 12. BILLING STATUS DISTRIBUTION
-- ============================================================

SELECT
    payment_status,
    COUNT(*) AS bill_count
FROM core.billing_transactions
GROUP BY payment_status
ORDER BY payment_status;