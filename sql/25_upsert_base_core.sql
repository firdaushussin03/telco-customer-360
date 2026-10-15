-- TELCO CUSTOMER 360 - BASE CORE UPSERT
-- File: 25_upsert_base_core.sql

BEGIN;

INSERT INTO core.customer (
    customer_id, gender, age, under_30, senior_citizen, married,
    dependents, number_of_dependents, source_file_name,
    ingested_at, transformed_at
)
SELECT
    customer_id, gender, age, under_30, senior_citizen, married,
    dependents, number_of_dependents, source_file_name,
    ingested_at, transformed_at
FROM staging.demographics
ON CONFLICT (customer_id)
DO UPDATE SET
    gender = EXCLUDED.gender,
    age = EXCLUDED.age,
    under_30 = EXCLUDED.under_30,
    senior_citizen = EXCLUDED.senior_citizen,
    married = EXCLUDED.married,
    dependents = EXCLUDED.dependents,
    number_of_dependents = EXCLUDED.number_of_dependents,
    source_file_name = EXCLUDED.source_file_name,
    ingested_at = EXCLUDED.ingested_at,
    transformed_at = EXCLUDED.transformed_at;

INSERT INTO core.population (
    zip_code, population, source_file_name, ingested_at, transformed_at
)
SELECT
    LPAD(zip_code::TEXT, 5, '0'),
    population,
    source_file_name,
    ingested_at,
    transformed_at
FROM staging.population
ON CONFLICT (zip_code)
DO UPDATE SET
    population = EXCLUDED.population,
    source_file_name = EXCLUDED.source_file_name,
    ingested_at = EXCLUDED.ingested_at,
    transformed_at = EXCLUDED.transformed_at;

INSERT INTO core.location (
    location_id, customer_id, zip_code, country, state, city,
    latitude, longitude, source_file_name, ingested_at, transformed_at
)
SELECT
    location_id, customer_id, LPAD(zip_code::TEXT, 5, '0'),
    country, state, city, latitude, longitude,
    source_file_name, ingested_at, transformed_at
FROM staging.location
ON CONFLICT (customer_id)
DO UPDATE SET
    location_id = EXCLUDED.location_id,
    zip_code = EXCLUDED.zip_code,
    country = EXCLUDED.country,
    state = EXCLUDED.state,
    city = EXCLUDED.city,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    source_file_name = EXCLUDED.source_file_name,
    ingested_at = EXCLUDED.ingested_at,
    transformed_at = EXCLUDED.transformed_at;

INSERT INTO core.services (
    service_id, customer_id, quarter, referred_a_friend,
    number_of_referrals, tenure_in_months, offer, phone_service,
    avg_monthly_long_distance_charges, multiple_lines,
    internet_service, internet_type, avg_monthly_gb_download,
    online_security, online_backup, device_protection_plan,
    premium_tech_support, streaming_tv, streaming_movies,
    streaming_music, unlimited_data, contract, paperless_billing,
    payment_method, monthly_charge, total_charges, total_refunds,
    total_extra_data_charges, total_long_distance_charges,
    total_revenue, source_file_name, ingested_at, transformed_at
)
SELECT
    service_id, customer_id, quarter, referred_a_friend,
    number_of_referrals, tenure_in_months, offer, phone_service,
    avg_monthly_long_distance_charges, multiple_lines,
    internet_service, internet_type, avg_monthly_gb_download,
    online_security, online_backup, device_protection_plan,
    premium_tech_support, streaming_tv, streaming_movies,
    streaming_music, unlimited_data, contract, paperless_billing,
    payment_method, monthly_charge, total_charges, total_refunds,
    total_extra_data_charges, total_long_distance_charges,
    total_revenue, source_file_name, ingested_at, transformed_at
FROM staging.services
ON CONFLICT (customer_id)
DO UPDATE SET
    service_id = EXCLUDED.service_id,
    quarter = EXCLUDED.quarter,
    referred_a_friend = EXCLUDED.referred_a_friend,
    number_of_referrals = EXCLUDED.number_of_referrals,
    tenure_in_months = EXCLUDED.tenure_in_months,
    offer = EXCLUDED.offer,
    phone_service = EXCLUDED.phone_service,
    avg_monthly_long_distance_charges = EXCLUDED.avg_monthly_long_distance_charges,
    multiple_lines = EXCLUDED.multiple_lines,
    internet_service = EXCLUDED.internet_service,
    internet_type = EXCLUDED.internet_type,
    avg_monthly_gb_download = EXCLUDED.avg_monthly_gb_download,
    online_security = EXCLUDED.online_security,
    online_backup = EXCLUDED.online_backup,
    device_protection_plan = EXCLUDED.device_protection_plan,
    premium_tech_support = EXCLUDED.premium_tech_support,
    streaming_tv = EXCLUDED.streaming_tv,
    streaming_movies = EXCLUDED.streaming_movies,
    streaming_music = EXCLUDED.streaming_music,
    unlimited_data = EXCLUDED.unlimited_data,
    contract = EXCLUDED.contract,
    paperless_billing = EXCLUDED.paperless_billing,
    payment_method = EXCLUDED.payment_method,
    monthly_charge = EXCLUDED.monthly_charge,
    total_charges = EXCLUDED.total_charges,
    total_refunds = EXCLUDED.total_refunds,
    total_extra_data_charges = EXCLUDED.total_extra_data_charges,
    total_long_distance_charges = EXCLUDED.total_long_distance_charges,
    total_revenue = EXCLUDED.total_revenue,
    source_file_name = EXCLUDED.source_file_name,
    ingested_at = EXCLUDED.ingested_at,
    transformed_at = EXCLUDED.transformed_at;

INSERT INTO core.customer_status (
    status_id, customer_id, quarter, satisfaction_score,
    customer_status, churned, churn_score, cltv, churn_category,
    churn_reason, source_file_name, ingested_at, transformed_at
)
SELECT
    status_id, customer_id, quarter, satisfaction_score,
    customer_status, churned, churn_score, cltv, churn_category,
    churn_reason, source_file_name, ingested_at, transformed_at
FROM staging.status
ON CONFLICT (customer_id)
DO UPDATE SET
    status_id = EXCLUDED.status_id,
    quarter = EXCLUDED.quarter,
    satisfaction_score = EXCLUDED.satisfaction_score,
    customer_status = EXCLUDED.customer_status,
    churned = EXCLUDED.churned,
    churn_score = EXCLUDED.churn_score,
    cltv = EXCLUDED.cltv,
    churn_category = EXCLUDED.churn_category,
    churn_reason = EXCLUDED.churn_reason,
    source_file_name = EXCLUDED.source_file_name,
    ingested_at = EXCLUDED.ingested_at,
    transformed_at = EXCLUDED.transformed_at;

COMMIT;
