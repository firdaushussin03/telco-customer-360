CREATE TABLE raw.demographics (
    customer_id VARCHAR(20),
    count INTEGER,
    gender VARCHAR(20),
    age INTEGER,
    under_30 VARCHAR(10),
    senior_citizen VARCHAR(10),
    married VARCHAR(10),
    dependents VARCHAR(10),
    number_of_dependents INTEGER,

    source_file_name VARCHAR(255),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

	
	CREATE TABLE raw.location (
    location_id VARCHAR(20),
    customer_id VARCHAR(20),
    count INTEGER,
    country VARCHAR(100),
    state VARCHAR(100),
    city VARCHAR(100),
    zip_code INTEGER,
    lat_long VARCHAR(100),
    latitude NUMERIC(10,6),
    longitude NUMERIC(10,6),

    source_file_name VARCHAR(255),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE raw.population (
    id INTEGER,
    zip_code INTEGER,
    population INTEGER,

    source_file_name VARCHAR(255),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE raw.services (
    service_id VARCHAR(20),
    customer_id VARCHAR(20),
    count INTEGER,
    quarter VARCHAR(10),

    referred_a_friend VARCHAR(10),
    number_of_referrals INTEGER,
    tenure_in_months INTEGER,
    offer VARCHAR(20),

    phone_service VARCHAR(10),
    avg_monthly_long_distance_charges NUMERIC(12,2),
    multiple_lines VARCHAR(10),

    internet_service VARCHAR(10),
    internet_type VARCHAR(30),
    avg_monthly_gb_download INTEGER,

    online_security VARCHAR(10),
    online_backup VARCHAR(10),
    device_protection_plan VARCHAR(10),
    premium_tech_support VARCHAR(10),

    streaming_tv VARCHAR(10),
    streaming_movies VARCHAR(10),
    streaming_music VARCHAR(10),
    unlimited_data VARCHAR(10),

    contract VARCHAR(30),
    paperless_billing VARCHAR(10),
    payment_method VARCHAR(50),

    monthly_charge NUMERIC(12,2),
    total_charges NUMERIC(12,2),
    total_refunds NUMERIC(12,2),
    total_extra_data_charges NUMERIC(12,2),
    total_long_distance_charges NUMERIC(12,2),
    total_revenue NUMERIC(12,2),

    source_file_name VARCHAR(255),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE raw.status (
    status_id VARCHAR(20),
    customer_id VARCHAR(20),
    count INTEGER,
    quarter VARCHAR(10),

    satisfaction_score INTEGER,
    customer_status VARCHAR(30),

    churn_label VARCHAR(10),
    churn_value INTEGER,
    churn_score INTEGER,

    cltv INTEGER,

    churn_category VARCHAR(50),
    churn_reason VARCHAR(150),

    source_file_name VARCHAR(255),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);