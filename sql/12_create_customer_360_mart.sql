-- ============================================================
-- TELCO CUSTOMER 360 - CUSTOMER 360 MART
-- File: 12_create_customer_360_mart.sql
--
-- Grain:
--   1 row = 1 customer
--
-- Purpose:
--   Provide an analytics-ready customer-level dataset
--   by combining trusted CORE entities.
-- ============================================================


DROP TABLE IF EXISTS mart.customer_360;


CREATE TABLE mart.customer_360 AS
SELECT

    -- ========================================================
    -- CUSTOMER
    -- ========================================================

    c.customer_id,
    c.gender,
    c.age,

    c.under_30,
    c.senior_citizen,
    c.married,
    c.dependents,
    c.number_of_dependents,


    -- ========================================================
    -- LOCATION
    -- ========================================================

    l.country,
    l.state,
    l.city,
    l.zip_code,
    l.latitude,
    l.longitude,

    p.population AS zip_code_population,


    -- ========================================================
    -- SERVICES
    -- ========================================================

    s.quarter,

    s.referred_a_friend,
    s.number_of_referrals,

    s.tenure_in_months,
    s.offer,

    s.phone_service,
    s.multiple_lines,

    s.internet_service,
    s.internet_type,

    s.avg_monthly_gb_download,
    s.avg_monthly_long_distance_charges,

    s.online_security,
    s.online_backup,
    s.device_protection_plan,
    s.premium_tech_support,

    s.streaming_tv,
    s.streaming_movies,
    s.streaming_music,
    s.unlimited_data,

    s.contract,
    s.paperless_billing,
    s.payment_method,

    s.monthly_charge,
    s.total_charges,
    s.total_refunds,
    s.total_extra_data_charges,
    s.total_long_distance_charges,
    s.total_revenue,


    -- ========================================================
    -- CUSTOMER STATUS
    -- ========================================================

    cs.satisfaction_score,
    cs.customer_status,
    cs.churned,
    cs.churn_score,
    cs.cltv,
    cs.churn_category,
    cs.churn_reason,


    -- ========================================================
    -- ANALYTICAL DERIVED COLUMNS
    -- ========================================================

    CASE
        WHEN c.age < 30 THEN 'Under 30'
        WHEN c.age BETWEEN 30 AND 49 THEN '30-49'
        WHEN c.age BETWEEN 50 AND 64 THEN '50-64'
        ELSE '65+'
    END AS age_group,


    CASE
        WHEN s.tenure_in_months <= 12 THEN '0-12 Months'
        WHEN s.tenure_in_months <= 24 THEN '13-24 Months'
        WHEN s.tenure_in_months <= 48 THEN '25-48 Months'
        ELSE '49+ Months'
    END AS tenure_group,


    CURRENT_TIMESTAMP AS mart_loaded_at


FROM core.customer c


LEFT JOIN core.location l
    ON c.customer_id = l.customer_id


LEFT JOIN core.population p
    ON l.zip_code = p.zip_code


LEFT JOIN core.services s
    ON c.customer_id = s.customer_id


LEFT JOIN core.customer_status cs
    ON c.customer_id = cs.customer_id;