-- ============================================================
-- TELCO CUSTOMER 360 - STAGING TRANSFORMATION
-- File: 06_transform_staging.sql
-- ============================================================


-- ============================================================
-- 1. DEMOGRAPHICS
-- ============================================================

DROP TABLE IF EXISTS staging.demographics;

CREATE TABLE staging.demographics AS
SELECT
    customer_id,
    gender,
    age,

    CASE
        WHEN under_30 = 'Yes' THEN TRUE
        WHEN under_30 = 'No' THEN FALSE
        ELSE NULL
    END AS under_30,

    CASE
        WHEN senior_citizen = 'Yes' THEN TRUE
        WHEN senior_citizen = 'No' THEN FALSE
        ELSE NULL
    END AS senior_citizen,

    CASE
        WHEN married = 'Yes' THEN TRUE
        WHEN married = 'No' THEN FALSE
        ELSE NULL
    END AS married,

    CASE
        WHEN dependents = 'Yes' THEN TRUE
        WHEN dependents = 'No' THEN FALSE
        ELSE NULL
    END AS dependents,

    number_of_dependents,

    source_file_name,
    ingested_at,
    CURRENT_TIMESTAMP AS transformed_at

FROM raw.demographics;

-- ============================================================
-- 2. LOCATION
-- ============================================================

DROP TABLE IF EXISTS staging.location;

CREATE TABLE staging.location AS
SELECT
    location_id,
    customer_id,
    country,
    state,
    city,
    zip_code,
    latitude,
    longitude,

    source_file_name,
    ingested_at,
    CURRENT_TIMESTAMP AS transformed_at

FROM raw.location;

-- ============================================================
-- 3. POPULATION
-- ============================================================

DROP TABLE IF EXISTS staging.population;

CREATE TABLE staging.population AS
SELECT
    zip_code,
    population,

    source_file_name,
    ingested_at,
    CURRENT_TIMESTAMP AS transformed_at

FROM raw.population;

-- ============================================================
-- 4. SERVICES
-- ============================================================

DROP TABLE IF EXISTS staging.services;

CREATE TABLE staging.services AS
SELECT
    service_id,
    customer_id,
    quarter,

    CASE
        WHEN referred_a_friend = 'Yes' THEN TRUE
        WHEN referred_a_friend = 'No' THEN FALSE
        ELSE NULL
    END AS referred_a_friend,

    number_of_referrals,
    tenure_in_months,
    offer,

    CASE
        WHEN phone_service = 'Yes' THEN TRUE
        WHEN phone_service = 'No' THEN FALSE
        ELSE NULL
    END AS phone_service,

    avg_monthly_long_distance_charges,

    CASE
        WHEN multiple_lines = 'Yes' THEN TRUE
        WHEN multiple_lines = 'No' THEN FALSE
        ELSE NULL
    END AS multiple_lines,

    CASE
        WHEN internet_service = 'Yes' THEN TRUE
        WHEN internet_service = 'No' THEN FALSE
        ELSE NULL
    END AS internet_service,

    internet_type,
    avg_monthly_gb_download,

    CASE
        WHEN online_security = 'Yes' THEN TRUE
        WHEN online_security = 'No' THEN FALSE
        ELSE NULL
    END AS online_security,

    CASE
        WHEN online_backup = 'Yes' THEN TRUE
        WHEN online_backup = 'No' THEN FALSE
        ELSE NULL
    END AS online_backup,

    CASE
        WHEN device_protection_plan = 'Yes' THEN TRUE
        WHEN device_protection_plan = 'No' THEN FALSE
        ELSE NULL
    END AS device_protection_plan,

    CASE
        WHEN premium_tech_support = 'Yes' THEN TRUE
        WHEN premium_tech_support = 'No' THEN FALSE
        ELSE NULL
    END AS premium_tech_support,

    CASE
        WHEN streaming_tv = 'Yes' THEN TRUE
        WHEN streaming_tv = 'No' THEN FALSE
        ELSE NULL
    END AS streaming_tv,

    CASE
        WHEN streaming_movies = 'Yes' THEN TRUE
        WHEN streaming_movies = 'No' THEN FALSE
        ELSE NULL
    END AS streaming_movies,

    CASE
        WHEN streaming_music = 'Yes' THEN TRUE
        WHEN streaming_music = 'No' THEN FALSE
        ELSE NULL
    END AS streaming_music,

    CASE
        WHEN unlimited_data = 'Yes' THEN TRUE
        WHEN unlimited_data = 'No' THEN FALSE
        ELSE NULL
    END AS unlimited_data,

    contract,

    CASE
        WHEN paperless_billing = 'Yes' THEN TRUE
        WHEN paperless_billing = 'No' THEN FALSE
        ELSE NULL
    END AS paperless_billing,

    payment_method,

    monthly_charge,
    total_charges,
    total_refunds,
    total_extra_data_charges,
    total_long_distance_charges,
    total_revenue,

    source_file_name,
    ingested_at,
    CURRENT_TIMESTAMP AS transformed_at

FROM raw.services;

-- ============================================================
-- 5. STATUS
-- ============================================================

DROP TABLE IF EXISTS staging.status;

CREATE TABLE staging.status AS
SELECT
    status_id,
    customer_id,
    quarter,
    satisfaction_score,
    customer_status,

    CASE
        WHEN churn_label = 'Yes' THEN TRUE
        WHEN churn_label = 'No' THEN FALSE
        ELSE NULL
    END AS churned,

    churn_value,
    churn_score,
    cltv,
    churn_category,
    churn_reason,

    source_file_name,
    ingested_at,
    CURRENT_TIMESTAMP AS transformed_at

FROM raw.status;