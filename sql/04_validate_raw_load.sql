-- ============================================================
-- TELCO CUSTOMER 360 - RAW LOAD VALIDATION
-- File: 04_validate_raw_load.sql
-- Purpose:
--   - Validate row counts
--   - Validate duplicate keys
--   - Validate missing keys
--   - Validate relationships
--   - Validate expected NULL values
--   - Validate ingestion metadata
-- ============================================================


-- ============================================================
-- 1. ROW COUNT VALIDATION
-- ============================================================

SELECT 'demographics' AS table_name, COUNT(*) AS row_count
FROM raw.demographics

UNION ALL

SELECT 'location', COUNT(*)
FROM raw.location

UNION ALL

SELECT 'population', COUNT(*)
FROM raw.population

UNION ALL

SELECT 'services', COUNT(*)
FROM raw.services

UNION ALL

SELECT 'status', COUNT(*)
FROM raw.status;


-- Expected:
-- demographics = 7043
-- location     = 7043
-- population   = 1671
-- services     = 7043
-- status       = 7043



-- ============================================================
-- 2. DUPLICATE PRIMARY KEY CANDIDATES
-- ============================================================

-- demographics
SELECT customer_id, COUNT(*) AS total
FROM raw.demographics
GROUP BY customer_id
HAVING COUNT(*) > 1;


-- location
SELECT location_id, COUNT(*) AS total
FROM raw.location
GROUP BY location_id
HAVING COUNT(*) > 1;


-- population
SELECT zip_code, COUNT(*) AS total
FROM raw.population
GROUP BY zip_code
HAVING COUNT(*) > 1;


-- services
SELECT service_id, COUNT(*) AS total
FROM raw.services
GROUP BY service_id
HAVING COUNT(*) > 1;


-- status
SELECT status_id, COUNT(*) AS total
FROM raw.status
GROUP BY status_id
HAVING COUNT(*) > 1;


-- Expected:
-- All queries should return 0 rows.



-- ============================================================
-- 3. MISSING KEY VALIDATION
-- ============================================================

SELECT COUNT(*) AS missing_customer_ids
FROM raw.demographics
WHERE customer_id IS NULL;


SELECT COUNT(*) AS missing_location_ids
FROM raw.location
WHERE location_id IS NULL;


SELECT COUNT(*) AS missing_zip_codes
FROM raw.population
WHERE zip_code IS NULL;


SELECT COUNT(*) AS missing_service_ids
FROM raw.services
WHERE service_id IS NULL;


SELECT COUNT(*) AS missing_status_ids
FROM raw.status
WHERE status_id IS NULL;


-- Expected:
-- All should return 0.



-- ============================================================
-- 4. CUSTOMER ID UNIQUENESS
-- ============================================================

SELECT customer_id, COUNT(*) AS total
FROM raw.location
GROUP BY customer_id
HAVING COUNT(*) > 1;


SELECT customer_id, COUNT(*) AS total
FROM raw.services
GROUP BY customer_id
HAVING COUNT(*) > 1;


SELECT customer_id, COUNT(*) AS total
FROM raw.status
GROUP BY customer_id
HAVING COUNT(*) > 1;


-- Expected:
-- 0 rows from each query.



-- ============================================================
-- 5. RELATIONSHIP VALIDATION
-- ============================================================

-- Location customers that do not exist in demographics
SELECT l.customer_id
FROM raw.location l
LEFT JOIN raw.demographics d
    ON l.customer_id = d.customer_id
WHERE d.customer_id IS NULL;


-- Services customers that do not exist in demographics
SELECT s.customer_id
FROM raw.services s
LEFT JOIN raw.demographics d
    ON s.customer_id = d.customer_id
WHERE d.customer_id IS NULL;


-- Status customers that do not exist in demographics
SELECT s.customer_id
FROM raw.status s
LEFT JOIN raw.demographics d
    ON s.customer_id = d.customer_id
WHERE d.customer_id IS NULL;


-- Location Zip Codes that do not exist in population
SELECT DISTINCT l.zip_code
FROM raw.location l
LEFT JOIN raw.population p
    ON l.zip_code = p.zip_code
WHERE p.zip_code IS NULL;


-- Expected:
-- All should return 0 rows.



-- ============================================================
-- 6. EXPECTED NULL VALUES
-- ============================================================

-- Services
SELECT
    COUNT(*) FILTER (WHERE offer IS NULL) AS null_offer,
    COUNT(*) FILTER (WHERE internet_type IS NULL) AS null_internet_type
FROM raw.services;


-- Expected from source:
-- offer         = 3877
-- internet_type = 1526


-- Status
SELECT
    COUNT(*) FILTER (WHERE churn_category IS NULL)
        AS null_churn_category,

    COUNT(*) FILTER (WHERE churn_reason IS NULL)
        AS null_churn_reason
FROM raw.status;


-- Expected from source:
-- churn_category = 5174
-- churn_reason   = 5174



-- ============================================================
-- 7. BUSINESS MEANING OF NULLS
-- ============================================================

-- Customers without Internet Service should explain
-- most/all NULL Internet Type values.

SELECT
    internet_service,
    COUNT(*) AS customers,
    COUNT(*) FILTER (WHERE internet_type IS NULL)
        AS null_internet_type
FROM raw.services
GROUP BY internet_service
ORDER BY internet_service;


-- Examine churn NULL behaviour.

SELECT
    churn_label,
    COUNT(*) AS customers,
    COUNT(*) FILTER (WHERE churn_category IS NULL)
        AS null_churn_category,
    COUNT(*) FILTER (WHERE churn_reason IS NULL)
        AS null_churn_reason
FROM raw.status
GROUP BY churn_label
ORDER BY churn_label;



-- ============================================================
-- 8. INGESTION METADATA VALIDATION
-- ============================================================

SELECT
    source_file_name,
    COUNT(*) AS rows_loaded,
    MIN(ingested_at) AS first_ingested_at,
    MAX(ingested_at) AS last_ingested_at
FROM raw.demographics
GROUP BY source_file_name;


SELECT
    source_file_name,
    COUNT(*) AS rows_loaded,
    MIN(ingested_at) AS first_ingested_at,
    MAX(ingested_at) AS last_ingested_at
FROM raw.location
GROUP BY source_file_name;


SELECT
    source_file_name,
    COUNT(*) AS rows_loaded,
    MIN(ingested_at) AS first_ingested_at,
    MAX(ingested_at) AS last_ingested_at
FROM raw.population
GROUP BY source_file_name;


SELECT
    source_file_name,
    COUNT(*) AS rows_loaded,
    MIN(ingested_at) AS first_ingested_at,
    MAX(ingested_at) AS last_ingested_at
FROM raw.services
GROUP BY source_file_name;


SELECT
    source_file_name,
    COUNT(*) AS rows_loaded,
    MIN(ingested_at) AS first_ingested_at,
    MAX(ingested_at) AS last_ingested_at
FROM raw.status
GROUP BY source_file_name;