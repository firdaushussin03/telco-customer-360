-- ============================================================
-- TELCO CUSTOMER 360 - STAGING VALIDATION
-- File: 07_validate_staging.sql
-- Purpose:
--   - Validate row counts after transformation
--   - Validate Boolean conversions
--   - Validate business rules
--   - Detect unexpected NULLs
--   - Validate churn transformation
-- ============================================================


-- ============================================================
-- 1. ROW COUNT VALIDATION
-- ============================================================

SELECT 'demographics' AS table_name, COUNT(*) AS row_count
FROM staging.demographics

UNION ALL

SELECT 'location', COUNT(*)
FROM staging.location

UNION ALL

SELECT 'population', COUNT(*)
FROM staging.population

UNION ALL

SELECT 'services', COUNT(*)
FROM staging.services

UNION ALL

SELECT 'status', COUNT(*)
FROM staging.status;


-- Expected:
-- demographics = 7043
-- location     = 7043
-- population   = 1671
-- services     = 7043
-- status       = 7043



-- ============================================================
-- 2. RAW VS STAGING ROW COUNTS
-- ============================================================

SELECT
    (SELECT COUNT(*) FROM raw.demographics) AS raw_count,
    (SELECT COUNT(*) FROM staging.demographics) AS staging_count;


SELECT
    (SELECT COUNT(*) FROM raw.location) AS raw_count,
    (SELECT COUNT(*) FROM staging.location) AS staging_count;


SELECT
    (SELECT COUNT(*) FROM raw.population) AS raw_count,
    (SELECT COUNT(*) FROM staging.population) AS staging_count;


SELECT
    (SELECT COUNT(*) FROM raw.services) AS raw_count,
    (SELECT COUNT(*) FROM staging.services) AS staging_count;


SELECT
    (SELECT COUNT(*) FROM raw.status) AS raw_count,
    (SELECT COUNT(*) FROM staging.status) AS staging_count;


-- Expected:
-- RAW count = STAGING count for every table.



-- ============================================================
-- 3. DEMOGRAPHICS BOOLEAN VALIDATION
-- ============================================================

SELECT
    under_30,
    COUNT(*) AS total
FROM staging.demographics
GROUP BY under_30
ORDER BY under_30;


SELECT
    senior_citizen,
    COUNT(*) AS total
FROM staging.demographics
GROUP BY senior_citizen
ORDER BY senior_citizen;


SELECT
    married,
    COUNT(*) AS total
FROM staging.demographics
GROUP BY married
ORDER BY married;


SELECT
    dependents,
    COUNT(*) AS total
FROM staging.demographics
GROUP BY dependents
ORDER BY dependents;


-- Expected:
-- Only TRUE / FALSE.
-- No unexpected NULL values.



-- ============================================================
-- 4. CHECK BOOLEAN CONVERSION AGAINST RAW
-- ============================================================

SELECT COUNT(*) AS invalid_under_30_conversion
FROM raw.demographics r
JOIN staging.demographics s
    ON r.customer_id = s.customer_id
WHERE
    (r.under_30 = 'Yes' AND s.under_30 IS NOT TRUE)
    OR
    (r.under_30 = 'No' AND s.under_30 IS NOT FALSE);


SELECT COUNT(*) AS invalid_senior_conversion
FROM raw.demographics r
JOIN staging.demographics s
    ON r.customer_id = s.customer_id
WHERE
    (r.senior_citizen = 'Yes'
        AND s.senior_citizen IS NOT TRUE)
    OR
    (r.senior_citizen = 'No'
        AND s.senior_citizen IS NOT FALSE);


SELECT COUNT(*) AS invalid_married_conversion
FROM raw.demographics r
JOIN staging.demographics s
    ON r.customer_id = s.customer_id
WHERE
    (r.married = 'Yes' AND s.married IS NOT TRUE)
    OR
    (r.married = 'No' AND s.married IS NOT FALSE);


SELECT COUNT(*) AS invalid_dependents_conversion
FROM raw.demographics r
JOIN staging.demographics s
    ON r.customer_id = s.customer_id
WHERE
    (r.dependents = 'Yes' AND s.dependents IS NOT TRUE)
    OR
    (r.dependents = 'No' AND s.dependents IS NOT FALSE);


-- Expected:
-- All = 0



-- ============================================================
-- 5. SERVICES BOOLEAN NULL VALIDATION
-- ============================================================

SELECT
    COUNT(*) FILTER (
        WHERE referred_a_friend IS NULL
    ) AS null_referred_a_friend,

    COUNT(*) FILTER (
        WHERE phone_service IS NULL
    ) AS null_phone_service,

    COUNT(*) FILTER (
        WHERE multiple_lines IS NULL
    ) AS null_multiple_lines,

    COUNT(*) FILTER (
        WHERE internet_service IS NULL
    ) AS null_internet_service,

    COUNT(*) FILTER (
        WHERE online_security IS NULL
    ) AS null_online_security,

    COUNT(*) FILTER (
        WHERE online_backup IS NULL
    ) AS null_online_backup,

    COUNT(*) FILTER (
        WHERE device_protection_plan IS NULL
    ) AS null_device_protection,

    COUNT(*) FILTER (
        WHERE premium_tech_support IS NULL
    ) AS null_tech_support,

    COUNT(*) FILTER (
        WHERE streaming_tv IS NULL
    ) AS null_streaming_tv,

    COUNT(*) FILTER (
        WHERE streaming_movies IS NULL
    ) AS null_streaming_movies,

    COUNT(*) FILTER (
        WHERE streaming_music IS NULL
    ) AS null_streaming_music,

    COUNT(*) FILTER (
        WHERE unlimited_data IS NULL
    ) AS null_unlimited_data,

    COUNT(*) FILTER (
        WHERE paperless_billing IS NULL
    ) AS null_paperless_billing

FROM staging.services;


-- Expected:
-- All should be 0.
--
-- Because the RAW values for these columns
-- contained only Yes / No.



-- ============================================================
-- 6. INTERNET SERVICE BUSINESS RULE
-- ============================================================

SELECT
    internet_service,
    COUNT(*) AS customers,
    COUNT(*) FILTER (
        WHERE internet_type IS NULL
    ) AS null_internet_type
FROM staging.services
GROUP BY internet_service
ORDER BY internet_service;


-- Expected:
--
-- FALSE = 1526 customers
-- NULL internet_type = 1526
--
-- TRUE = 5517 customers
-- NULL internet_type = 0



-- Find actual violations if any.

SELECT
    customer_id,
    internet_service,
    internet_type
FROM staging.services
WHERE
    (internet_service = FALSE AND internet_type IS NOT NULL)
    OR
    (internet_service = TRUE AND internet_type IS NULL);


-- Expected:
-- 0 rows



-- ============================================================
-- 7. CHURN BOOLEAN VALIDATION
-- ============================================================

SELECT
    churned,
    COUNT(*) AS total
FROM staging.status
GROUP BY churned
ORDER BY churned;


-- Expected:
--
-- FALSE = 5174
-- TRUE  = 1869



-- ============================================================
-- 8. CHURNED VS CHURN VALUE
-- ============================================================

SELECT COUNT(*) AS invalid_churn_mapping
FROM staging.status
WHERE
    (churned = TRUE AND churn_value <> 1)
    OR
    (churned = FALSE AND churn_value <> 0);


-- Expected:
-- 0



-- Optional: inspect any incorrect rows.

SELECT
    customer_id,
    customer_status,
    churned,
    churn_value
FROM staging.status
WHERE
    (churned = TRUE AND churn_value <> 1)
    OR
    (churned = FALSE AND churn_value <> 0);


-- Expected:
-- 0 rows



-- ============================================================
-- 9. CHURN CATEGORY / REASON BUSINESS RULE
-- ============================================================

SELECT
    churned,
    COUNT(*) AS customers,

    COUNT(*) FILTER (
        WHERE churn_category IS NULL
    ) AS null_churn_category,

    COUNT(*) FILTER (
        WHERE churn_reason IS NULL
    ) AS null_churn_reason

FROM staging.status
GROUP BY churned
ORDER BY churned;


-- Expected:
--
-- churned = FALSE
-- customers = 5174
-- category NULL = 5174
-- reason NULL   = 5174
--
-- churned = TRUE
-- customers = 1869
-- category NULL = 0
-- reason NULL   = 0



-- Detect violations.

SELECT
    customer_id,
    churned,
    churn_category,
    churn_reason
FROM staging.status
WHERE
    (churned = TRUE
        AND (churn_category IS NULL OR churn_reason IS NULL))
    OR
    (churned = FALSE
        AND (churn_category IS NOT NULL OR churn_reason IS NOT NULL));


-- Expected:
-- 0 rows



-- ============================================================
-- 10. KEY UNIQUENESS
-- ============================================================

SELECT customer_id, COUNT(*)
FROM staging.demographics
GROUP BY customer_id
HAVING COUNT(*) > 1;


SELECT location_id, COUNT(*)
FROM staging.location
GROUP BY location_id
HAVING COUNT(*) > 1;


SELECT zip_code, COUNT(*)
FROM staging.population
GROUP BY zip_code
HAVING COUNT(*) > 1;


SELECT service_id, COUNT(*)
FROM staging.services
GROUP BY service_id
HAVING COUNT(*) > 1;


SELECT status_id, COUNT(*)
FROM staging.status
GROUP BY status_id
HAVING COUNT(*) > 1;


-- Expected:
-- 0 rows for all.



-- ============================================================
-- 11. TRANSFORMATION METADATA
-- ============================================================

SELECT
    source_file_name,
    MIN(ingested_at) AS ingested_at,
    MIN(transformed_at) AS transformed_at,
    COUNT(*) AS rows_transformed
FROM staging.demographics
GROUP BY source_file_name;


SELECT
    source_file_name,
    MIN(ingested_at) AS ingested_at,
    MIN(transformed_at) AS transformed_at,
    COUNT(*) AS rows_transformed
FROM staging.services
GROUP BY source_file_name;


SELECT
    source_file_name,
    MIN(ingested_at) AS ingested_at,
    MIN(transformed_at) AS transformed_at,
    COUNT(*) AS rows_transformed
FROM staging.status
GROUP BY source_file_name;