-- ============================================================
-- TELCO CUSTOMER 360 - CORE VALIDATION
-- File: 10_validate_core.sql
-- Purpose:
--   - Validate row counts
--   - Validate primary keys
--   - Validate foreign key relationships
--   - Validate 1:1 relationships
--   - Validate business rules
--   - Validate transformation lineage
-- ============================================================


-- ============================================================
-- 1. ROW COUNT VALIDATION
-- ============================================================

SELECT 'customer' AS table_name, COUNT(*) AS row_count
FROM core.customer

UNION ALL

SELECT 'location', COUNT(*)
FROM core.location

UNION ALL

SELECT 'population', COUNT(*)
FROM core.population

UNION ALL

SELECT 'services', COUNT(*)
FROM core.services

UNION ALL

SELECT 'customer_status', COUNT(*)
FROM core.customer_status;


-- Expected:
-- customer        = 7043
-- location        = 7043
-- population      = 1671
-- services        = 7043
-- customer_status = 7043



-- ============================================================
-- 2. STAGING VS CORE ROW COUNTS
-- ============================================================

SELECT
    (SELECT COUNT(*) FROM staging.demographics) AS staging_count,
    (SELECT COUNT(*) FROM core.customer) AS core_count;


SELECT
    (SELECT COUNT(*) FROM staging.location) AS staging_count,
    (SELECT COUNT(*) FROM core.location) AS core_count;


SELECT
    (SELECT COUNT(*) FROM staging.population) AS staging_count,
    (SELECT COUNT(*) FROM core.population) AS core_count;


SELECT
    (SELECT COUNT(*) FROM staging.services) AS staging_count,
    (SELECT COUNT(*) FROM core.services) AS core_count;


SELECT
    (SELECT COUNT(*) FROM staging.status) AS staging_count,
    (SELECT COUNT(*) FROM core.customer_status) AS core_count;


-- Expected:
-- staging_count = core_count for all tables



-- ============================================================
-- 3. PRIMARY KEY VALIDATION
-- ============================================================

SELECT customer_id, COUNT(*)
FROM core.customer
GROUP BY customer_id
HAVING COUNT(*) > 1;


SELECT location_id, COUNT(*)
FROM core.location
GROUP BY location_id
HAVING COUNT(*) > 1;


SELECT zip_code, COUNT(*)
FROM core.population
GROUP BY zip_code
HAVING COUNT(*) > 1;


SELECT service_id, COUNT(*)
FROM core.services
GROUP BY service_id
HAVING COUNT(*) > 1;


SELECT status_id, COUNT(*)
FROM core.customer_status
GROUP BY status_id
HAVING COUNT(*) > 1;


-- Expected:
-- 0 rows for every query



-- ============================================================
-- 4. FOREIGN KEY / REFERENTIAL INTEGRITY VALIDATION
-- ============================================================

-- Location customer must exist in customer
SELECT l.customer_id
FROM core.location l
LEFT JOIN core.customer c
    ON l.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- Service customer must exist in customer
SELECT s.customer_id
FROM core.services s
LEFT JOIN core.customer c
    ON s.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- Customer status must belong to an existing customer
SELECT cs.customer_id
FROM core.customer_status cs
LEFT JOIN core.customer c
    ON cs.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- Location Zip Code must exist in population
SELECT DISTINCT l.zip_code
FROM core.location l
LEFT JOIN core.population p
    ON l.zip_code = p.zip_code
WHERE p.zip_code IS NULL;


-- Expected:
-- 0 rows for every query



-- ============================================================
-- 5. 1:1 RELATIONSHIP VALIDATION
-- ============================================================

SELECT customer_id, COUNT(*) AS total
FROM core.location
GROUP BY customer_id
HAVING COUNT(*) > 1;


SELECT customer_id, COUNT(*) AS total
FROM core.services
GROUP BY customer_id
HAVING COUNT(*) > 1;


SELECT customer_id, COUNT(*) AS total
FROM core.customer_status
GROUP BY customer_id
HAVING COUNT(*) > 1;


-- Expected:
-- 0 rows



-- ============================================================
-- 6. CUSTOMER BUSINESS RULES
-- ============================================================

SELECT *
FROM core.customer
WHERE age < 0
   OR age > 120;


SELECT *
FROM core.customer
WHERE number_of_dependents < 0;


-- Expected:
-- 0 rows



-- ============================================================
-- 7. CHECK UNDER-30 BUSINESS LOGIC
-- ============================================================

SELECT
    customer_id,
    age,
    under_30
FROM core.customer
WHERE
    (age < 30 AND under_30 = FALSE)
    OR
    (age >= 30 AND under_30 = TRUE);


-- Expected:
-- Ideally 0 rows



-- ============================================================
-- 8. CHECK SENIOR CITIZEN LOGIC
-- ============================================================

SELECT
    customer_id,
    age,
    senior_citizen
FROM core.customer
WHERE
    (age >= 65 AND senior_citizen = FALSE)
    OR
    (age < 65 AND senior_citizen = TRUE);


-- Expected:
-- Check result.
--
-- Do not automatically assume age 65 if the source dataset
-- uses a different business definition. If rows appear,
-- investigate before changing anything.



-- ============================================================
-- 9. SERVICES NUMERIC RULES
-- ============================================================

SELECT *
FROM core.services
WHERE number_of_referrals < 0
   OR tenure_in_months < 0
   OR avg_monthly_gb_download < 0
   OR avg_monthly_long_distance_charges < 0
   OR monthly_charge < 0
   OR total_charges < 0
   OR total_refunds < 0
   OR total_extra_data_charges < 0
   OR total_long_distance_charges < 0
   OR total_revenue < 0;


-- Expected:
-- 0 rows



-- ============================================================
-- 10. INTERNET SERVICE BUSINESS RULE
-- ============================================================

SELECT
    customer_id,
    internet_service,
    internet_type
FROM core.services
WHERE
    (internet_service = FALSE AND internet_type IS NOT NULL)
    OR
    (internet_service = TRUE AND internet_type IS NULL);


-- Expected:
-- 0 rows



-- ============================================================
-- 11. STATUS BUSINESS RULES
-- ============================================================

SELECT *
FROM core.customer_status
WHERE satisfaction_score < 1
   OR satisfaction_score > 5;


SELECT *
FROM core.customer_status
WHERE churn_score < 0
   OR churn_score > 100;


SELECT *
FROM core.customer_status
WHERE cltv < 0;


-- Expected:
-- 0 rows



-- ============================================================
-- 12. CHURN BUSINESS RULE
-- ============================================================

SELECT
    customer_id,
    customer_status,
    churned,
    churn_category,
    churn_reason
FROM core.customer_status
WHERE
    (
        churned = TRUE
        AND (
            churn_category IS NULL
            OR churn_reason IS NULL
        )
    )
    OR
    (
        churned = FALSE
        AND (
            churn_category IS NOT NULL
            OR churn_reason IS NOT NULL
        )
    );


-- Expected:
-- 0 rows



-- ============================================================
-- 13. CUSTOMER STATUS VS CHURNED
-- ============================================================

SELECT
    customer_status,
    churned,
    COUNT(*) AS total
FROM core.customer_status
GROUP BY customer_status, churned
ORDER BY customer_status, churned;


-- We expect Churned customers to have churned = TRUE.
-- Joined / Stayed should normally be FALSE.



-- ============================================================
-- 14. ZIP CODE FORMAT
-- ============================================================

SELECT *
FROM core.population
WHERE LENGTH(zip_code) <> 5;


SELECT *
FROM core.location
WHERE LENGTH(zip_code) <> 5;


-- Expected:
-- 0 rows



-- ============================================================
-- 15. METADATA / DATA LINEAGE
-- ============================================================

SELECT
    source_file_name,
    COUNT(*) AS rows_loaded,
    MIN(ingested_at) AS ingested_at,
    MIN(transformed_at) AS transformed_at,
    MIN(core_loaded_at) AS core_loaded_at
FROM core.customer
GROUP BY source_file_name;


SELECT
    source_file_name,
    COUNT(*) AS rows_loaded,
    MIN(ingested_at) AS ingested_at,
    MIN(transformed_at) AS transformed_at,
    MIN(core_loaded_at) AS core_loaded_at
FROM core.services
GROUP BY source_file_name;


SELECT
    source_file_name,
    COUNT(*) AS rows_loaded,
    MIN(ingested_at) AS ingested_at,
    MIN(transformed_at) AS transformed_at,
    MIN(core_loaded_at) AS core_loaded_at
FROM core.customer_status
GROUP BY source_file_name;