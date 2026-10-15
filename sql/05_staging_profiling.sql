CREATE SCHEMA IF NOT EXISTS staging;

-- ============================================================
-- DEMOGRAPHICS PROFILING
-- ============================================================

SELECT count, COUNT(*) AS total
FROM raw.demographics
GROUP BY count
ORDER BY count;


SELECT gender, COUNT(*) AS total
FROM raw.demographics
GROUP BY gender
ORDER BY gender;


SELECT under_30, COUNT(*) AS total
FROM raw.demographics
GROUP BY under_30
ORDER BY under_30;


SELECT senior_citizen, COUNT(*) AS total
FROM raw.demographics
GROUP BY senior_citizen
ORDER BY senior_citizen;


SELECT married, COUNT(*) AS total
FROM raw.demographics
GROUP BY married
ORDER BY married;


SELECT dependents, COUNT(*) AS total
FROM raw.demographics
GROUP BY dependents
ORDER BY dependents;


SELECT
    MIN(age) AS min_age,
    MAX(age) AS max_age,
    MIN(number_of_dependents) AS min_dependents,
    MAX(number_of_dependents) AS max_dependents
FROM raw.demographics;

-- ============================================================
-- LOCATION PROFILING
-- ============================================================

SELECT count, COUNT(*) AS total
FROM raw.location
GROUP BY count
ORDER BY count;


SELECT country, COUNT(*) AS total
FROM raw.location
GROUP BY country
ORDER BY total DESC;


SELECT state, COUNT(*) AS total
FROM raw.location
GROUP BY state
ORDER BY total DESC;


SELECT
    MIN(latitude) AS min_latitude,
    MAX(latitude) AS max_latitude,
    MIN(longitude) AS min_longitude,
    MAX(longitude) AS max_longitude
FROM raw.location;


SELECT COUNT(DISTINCT city) AS unique_cities,
       COUNT(DISTINCT zip_code) AS unique_zip_codes
FROM raw.location;

-- ============================================================
-- POPULATION PROFILING
-- ============================================================

SELECT
    MIN(population) AS min_population,
    MAX(population) AS max_population,
    AVG(population) AS avg_population
FROM raw.population;


SELECT COUNT(*) AS invalid_population
FROM raw.population
WHERE population < 0;

-- ============================================================
-- SERVICES PROFILING
-- ============================================================

SELECT count, COUNT(*) AS total
FROM raw.services
GROUP BY count
ORDER BY count;


SELECT quarter, COUNT(*) AS total
FROM raw.services
GROUP BY quarter
ORDER BY quarter;


SELECT referred_a_friend, COUNT(*) AS total
FROM raw.services
GROUP BY referred_a_friend
ORDER BY referred_a_friend;


SELECT offer, COUNT(*) AS total
FROM raw.services
GROUP BY offer
ORDER BY offer;


SELECT phone_service, COUNT(*) AS total
FROM raw.services
GROUP BY phone_service
ORDER BY phone_service;


SELECT multiple_lines, COUNT(*) AS total
FROM raw.services
GROUP BY multiple_lines
ORDER BY multiple_lines;


SELECT internet_service, COUNT(*) AS total
FROM raw.services
GROUP BY internet_service
ORDER BY internet_service;


SELECT internet_type, COUNT(*) AS total
FROM raw.services
GROUP BY internet_type
ORDER BY internet_type;

-- internet related field

SELECT online_security, COUNT(*) AS total
FROM raw.services
GROUP BY online_security
ORDER BY online_security;


SELECT online_backup, COUNT(*) AS total
FROM raw.services
GROUP BY online_backup
ORDER BY online_backup;


SELECT device_protection_plan, COUNT(*) AS total
FROM raw.services
GROUP BY device_protection_plan
ORDER BY device_protection_plan;


SELECT premium_tech_support, COUNT(*) AS total
FROM raw.services
GROUP BY premium_tech_support
ORDER BY premium_tech_support;


SELECT streaming_tv, COUNT(*) AS total
FROM raw.services
GROUP BY streaming_tv
ORDER BY streaming_tv;


SELECT streaming_movies, COUNT(*) AS total
FROM raw.services
GROUP BY streaming_movies
ORDER BY streaming_movies;


SELECT streaming_music, COUNT(*) AS total
FROM raw.services
GROUP BY streaming_music
ORDER BY streaming_music;


SELECT unlimited_data, COUNT(*) AS total
FROM raw.services
GROUP BY unlimited_data
ORDER BY unlimited_data;

-- contract / payment fields

SELECT contract, COUNT(*) AS total
FROM raw.services
GROUP BY contract
ORDER BY contract;


SELECT paperless_billing, COUNT(*) AS total
FROM raw.services
GROUP BY paperless_billing
ORDER BY paperless_billing;


SELECT payment_method, COUNT(*) AS total
FROM raw.services
GROUP BY payment_method
ORDER BY payment_method;

-- numeric ranges

SELECT
    MIN(number_of_referrals) AS min_referrals,
    MAX(number_of_referrals) AS max_referrals,

    MIN(tenure_in_months) AS min_tenure,
    MAX(tenure_in_months) AS max_tenure,

    MIN(avg_monthly_gb_download) AS min_gb_download,
    MAX(avg_monthly_gb_download) AS max_gb_download,

    MIN(monthly_charge) AS min_monthly_charge,
    MAX(monthly_charge) AS max_monthly_charge,

    MIN(total_charges) AS min_total_charges,
    MAX(total_charges) AS max_total_charges,

    MIN(total_refunds) AS min_refunds,
    MAX(total_refunds) AS max_refunds,

    MIN(total_extra_data_charges) AS min_extra_data,
    MAX(total_extra_data_charges) AS max_extra_data,

    MIN(total_long_distance_charges) AS min_long_distance,
    MAX(total_long_distance_charges) AS max_long_distance,

    MIN(total_revenue) AS min_revenue,
    MAX(total_revenue) AS max_revenue
FROM raw.services;

-- Negative amount

SELECT COUNT(*) AS invalid_negative_amounts
FROM raw.services
WHERE monthly_charge < 0
   OR total_charges < 0
   OR total_refunds < 0
   OR total_extra_data_charges < 0
   OR total_long_distance_charges < 0
   OR total_revenue < 0;

   -- ============================================================
-- STATUS PROFILING
-- ============================================================

SELECT count, COUNT(*) AS total
FROM raw.status
GROUP BY count
ORDER BY count;


SELECT quarter, COUNT(*) AS total
FROM raw.status
GROUP BY quarter
ORDER BY quarter;


SELECT satisfaction_score, COUNT(*) AS total
FROM raw.status
GROUP BY satisfaction_score
ORDER BY satisfaction_score;


SELECT customer_status, COUNT(*) AS total
FROM raw.status
GROUP BY customer_status
ORDER BY customer_status;


SELECT churn_label, COUNT(*) AS total
FROM raw.status
GROUP BY churn_label
ORDER BY churn_label;


SELECT churn_value, COUNT(*) AS total
FROM raw.status
GROUP BY churn_value
ORDER BY churn_value;


SELECT churn_category, COUNT(*) AS total
FROM raw.status
GROUP BY churn_category
ORDER BY total DESC NULLS LAST;

SELECT COUNT(DISTINCT churn_reason) AS unique_churn_reasons
FROM raw.status;

SELECT
    MIN(satisfaction_score) AS min_satisfaction,
    MAX(satisfaction_score) AS max_satisfaction,

    MIN(churn_score) AS min_churn_score,
    MAX(churn_score) AS max_churn_score,

    MIN(cltv) AS min_cltv,
    MAX(cltv) AS max_cltv
FROM raw.status;