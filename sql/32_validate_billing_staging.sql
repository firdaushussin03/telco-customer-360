
-- ============================================================
-- TELCO CUSTOMER 360 - BILLING STAGING VALIDATION
-- File: 32_validate_billing_staging.sql
--
-- Purpose:
--   - Check billing STAGING data before CORE UPSERT
--   - Ensure latest RAW bill versions are selected
--   - Detect missing or duplicate bills
-- ============================================================


-- ============================================================
-- 1. COMPARE DISTINCT RAW BILLS WITH STAGING
-- ============================================================

SELECT
    (
        SELECT COUNT(DISTINCT bill_id)
        FROM raw.billing_transactions
    ) AS raw_unique_bills,

    (
        SELECT COUNT(*)
        FROM staging.billing_transactions
    ) AS staging_rows;

-- Expected both 42258


-- ============================================================
-- 2. CHECK DUPLICATE BILL IDs IN STAGING
-- ============================================================

SELECT COUNT(*) AS duplicate_bill_ids
FROM (
    SELECT bill_id
    FROM staging.billing_transactions
    GROUP BY bill_id
    HAVING COUNT(*) > 1
) duplicates;

-- expected 
-- 0

-- ============================================================
-- 3. CHECK FOR OUTDATED STAGING RECORDS
-- ============================================================

SELECT COUNT(*) AS outdated_staging_rows
FROM staging.billing_transactions s
WHERE EXISTS (
    SELECT 1
    FROM raw.billing_transactions r
    WHERE r.bill_id = s.bill_id
      AND r.updated_at > s.updated_at
);

-- expected
-- 0


-- ============================================================
-- 4. CHECK FOR MISSING BILLS IN STAGING
-- ============================================================

SELECT COUNT(*) AS missing_staging_bills
FROM (
    SELECT DISTINCT bill_id
    FROM raw.billing_transactions
    WHERE bill_id IS NOT NULL
) r
LEFT JOIN staging.billing_transactions s
    ON r.bill_id = s.bill_id
WHERE s.bill_id IS NULL;

-- expected
-- 0


-- ============================================================
-- 5. CHECK MISSING BILL IDs / UPDATE TIMESTAMPS
-- ============================================================

SELECT COUNT(*) AS invalid_staging_rows
FROM staging.billing_transactions
WHERE bill_id IS NULL
   OR updated_at IS NULL;

-- expected 
-- 0