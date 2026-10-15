-- ============================================================
-- TELCO CUSTOMER 360 - CORE FULL REFRESH
-- File: 09_load_core.sql
-- Purpose:
--   - Safely refresh trusted CORE tables
--   - Allow the pipeline to be rerun
--   - Execute the refresh as one transaction
-- ============================================================

BEGIN;


-- ============================================================
-- 1. CLEAR EXISTING CORE DATA
-- ============================================================

TRUNCATE TABLE
    core.customer_status,
    core.services,
    core.location,
    core.population,
    core.customer;


-- ============================================================
-- 2. LOAD CUSTOMER
-- ============================================================

INSERT INTO core.customer (
    customer_id,
    gender,
    age,
    under_30,
    senior_citizen,
    married,
    dependents,
    number_of_dependents,
    source_file_name,
    ingested_at,
    transformed_at
)
SELECT
    customer_id,
    gender,
    age,
    under_30,
    senior_citizen,
    married,
    dependents,
    number_of_dependents,
    source_file_name,
    ingested_at,
    transformed_at
FROM staging.demographics;


-- ============================================================
-- 3. LOAD POPULATION
-- ============================================================

INSERT INTO core.population (
    zip_code,
    population,
    source_file_name,
    ingested_at,
    transformed_at
)
SELECT
    LPAD(zip_code::TEXT, 5, '0'),
    population,
    source_file_name,
    ingested_at,
    transformed_at
FROM staging.population;


-- ============================================================
-- 4. LOAD LOCATION
-- ============================================================

INSERT INTO core.location (
    location_id,
    customer_id,
    zip_code,
    country,
    state,
    city,
    latitude,
    longitude,
    source_file_name,
    ingested_at,
    transformed_at
)
SELECT
    location_id,
    customer_id,
    LPAD(zip_code::TEXT, 5, '0'),
    country,
    state,
    city,
    latitude,
    longitude,
    source_file_name,
    ingested_at,
    transformed_at
FROM staging.location;


-- ============================================================
-- 5. LOAD SERVICES
-- ============================================================

INSERT INTO core.services (
    service_id,
    customer_id,
    quarter,
    referred_a_friend,
    number_of_referrals,
    tenure_in_months,
    offer,
    phone_service,
    avg_monthly_long_distance_charges,
    multiple_lines,
    internet_service,
    internet_type,
    avg_monthly_gb_download,
    online_security,
    online_backup,
    device_protection_plan,
    premium_tech_support,
    streaming_tv,
    streaming_movies,
    streaming_music,
    unlimited_data,
    contract,
    paperless_billing,
    payment_method,
    monthly_charge,
    total_charges,
    total_refunds,
    total_extra_data_charges,
    total_long_distance_charges,
    total_revenue,
    source_file_name,
    ingested_at,
    transformed_at
)
SELECT
    service_id,
    customer_id,
    quarter,
    referred_a_friend,
    number_of_referrals,
    tenure_in_months,
    offer,
    phone_service,
    avg_monthly_long_distance_charges,
    multiple_lines,
    internet_service,
    internet_type,
    avg_monthly_gb_download,
    online_security,
    online_backup,
    device_protection_plan,
    premium_tech_support,
    streaming_tv,
    streaming_movies,
    streaming_music,
    unlimited_data,
    contract,
    paperless_billing,
    payment_method,
    monthly_charge,
    total_charges,
    total_refunds,
    total_extra_data_charges,
    total_long_distance_charges,
    total_revenue,
    source_file_name,
    ingested_at,
    transformed_at
FROM staging.services;


-- ============================================================
-- 6. LOAD CUSTOMER STATUS
-- ============================================================

INSERT INTO core.customer_status (
    status_id,
    customer_id,
    quarter,
    satisfaction_score,
    customer_status,
    churned,
    churn_score,
    cltv,
    churn_category,
    churn_reason,
    source_file_name,
    ingested_at,
    transformed_at
)
SELECT
    status_id,
    customer_id,
    quarter,
    satisfaction_score,
    customer_status,
    churned,
    churn_score,
    cltv,
    churn_category,
    churn_reason,
    source_file_name,
    ingested_at,
    transformed_at
FROM staging.status;


COMMIT;