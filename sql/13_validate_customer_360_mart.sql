-- ============================================================
-- TELCO CUSTOMER 360 - MART VALIDATION
-- File: 13_validate_customer_360_mart.sql
-- ============================================================


-- ============================================================
-- 1. ROW COUNT
-- ============================================================

SELECT COUNT(*) AS total_customers
FROM mart.customer_360;


-- Expected:
-- 7043

-- ============================================================
-- 2. GRAIN VALIDATION
-- ============================================================

SELECT customer_id, COUNT(*) AS total
FROM mart.customer_360
GROUP BY customer_id
HAVING COUNT(*) > 1;


-- Expected:
-- 0 rows

SELECT c.customer_id
FROM core.customer c

LEFT JOIN mart.customer_360 m
    ON c.customer_id = m.customer_id

WHERE m.customer_id IS NULL;

SELECT
    COUNT(*) FILTER (
        WHERE city IS NULL
    ) AS missing_location,

    COUNT(*) FILTER (
        WHERE contract IS NULL
    ) AS missing_service,

    COUNT(*) FILTER (
        WHERE customer_status IS NULL
    ) AS missing_status

FROM mart.customer_360;

SELECT
    age_group,
    COUNT(*) AS customers
FROM mart.customer_360
GROUP BY age_group
ORDER BY age_group;

SELECT *
FROM mart.customer_360
WHERE
    (age < 30 AND age_group <> 'Under 30')
    OR
    (age BETWEEN 30 AND 49 AND age_group <> '30-49')
    OR
    (age BETWEEN 50 AND 64 AND age_group <> '50-64')
    OR
    (age >= 65 AND age_group <> '65+');

	SELECT
    tenure_group,
    COUNT(*) AS customers
FROM mart.customer_360
GROUP BY tenure_group
ORDER BY tenure_group;

SELECT *
FROM mart.customer_360
WHERE
    (tenure_in_months <= 12
        AND tenure_group <> '0-12 Months')

    OR

    (tenure_in_months BETWEEN 13 AND 24
        AND tenure_group <> '13-24 Months')

    OR

    (tenure_in_months BETWEEN 25 AND 48
        AND tenure_group <> '25-48 Months')

    OR

    (tenure_in_months >= 49
        AND tenure_group <> '49+ Months');