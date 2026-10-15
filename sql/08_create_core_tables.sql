CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE core.customer (
    customer_id VARCHAR(20) PRIMARY KEY,

    gender VARCHAR(20) NOT NULL,

    age INTEGER NOT NULL
        CHECK (age BETWEEN 0 AND 120),

    under_30 BOOLEAN NOT NULL,
    senior_citizen BOOLEAN NOT NULL,
    married BOOLEAN NOT NULL,
    dependents BOOLEAN NOT NULL,

    number_of_dependents INTEGER NOT NULL
        CHECK (number_of_dependents >= 0),

    source_file_name VARCHAR(255) NOT NULL,
    ingested_at TIMESTAMP NOT NULL,
    transformed_at TIMESTAMP NOT NULL,

    core_loaded_at TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE core.population (
    zip_code VARCHAR(5) PRIMARY KEY,

    population INTEGER NOT NULL
        CHECK (population >= 0),

    source_file_name VARCHAR(255) NOT NULL,
    ingested_at TIMESTAMP NOT NULL,
    transformed_at TIMESTAMP NOT NULL,

    core_loaded_at TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE core.location (
    location_id VARCHAR(20) PRIMARY KEY,

    customer_id VARCHAR(20)
        NOT NULL UNIQUE,

    zip_code VARCHAR(5)
        NOT NULL,

    country VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,

    latitude NUMERIC(10,6) NOT NULL
        CHECK (latitude BETWEEN -90 AND 90),

    longitude NUMERIC(10,6) NOT NULL
        CHECK (longitude BETWEEN -180 AND 180),

    source_file_name VARCHAR(255) NOT NULL,
    ingested_at TIMESTAMP NOT NULL,
    transformed_at TIMESTAMP NOT NULL,

    core_loaded_at TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_location_customer
        FOREIGN KEY (customer_id)
        REFERENCES core.customer(customer_id),

    CONSTRAINT fk_location_population
        FOREIGN KEY (zip_code)
        REFERENCES core.population(zip_code)
);

CREATE TABLE core.services (
    service_id VARCHAR(20) PRIMARY KEY,

    customer_id VARCHAR(20)
        NOT NULL UNIQUE,

    quarter VARCHAR(10) NOT NULL,

    referred_a_friend BOOLEAN NOT NULL,

    number_of_referrals INTEGER NOT NULL
        CHECK (number_of_referrals >= 0),

    tenure_in_months INTEGER NOT NULL
        CHECK (tenure_in_months >= 0),

    offer VARCHAR(20),

    phone_service BOOLEAN NOT NULL,

    avg_monthly_long_distance_charges NUMERIC(12,2)
        NOT NULL
        CHECK (avg_monthly_long_distance_charges >= 0),

    multiple_lines BOOLEAN NOT NULL,

    internet_service BOOLEAN NOT NULL,

    internet_type VARCHAR(30),

    avg_monthly_gb_download INTEGER NOT NULL
        CHECK (avg_monthly_gb_download >= 0),

    online_security BOOLEAN NOT NULL,
    online_backup BOOLEAN NOT NULL,
    device_protection_plan BOOLEAN NOT NULL,
    premium_tech_support BOOLEAN NOT NULL,

    streaming_tv BOOLEAN NOT NULL,
    streaming_movies BOOLEAN NOT NULL,
    streaming_music BOOLEAN NOT NULL,
    unlimited_data BOOLEAN NOT NULL,

    contract VARCHAR(30) NOT NULL,

    paperless_billing BOOLEAN NOT NULL,

    payment_method VARCHAR(50) NOT NULL,

    monthly_charge NUMERIC(12,2)
        NOT NULL CHECK (monthly_charge >= 0),

    total_charges NUMERIC(12,2)
        NOT NULL CHECK (total_charges >= 0),

    total_refunds NUMERIC(12,2)
        NOT NULL CHECK (total_refunds >= 0),

    total_extra_data_charges NUMERIC(12,2)
        NOT NULL CHECK (total_extra_data_charges >= 0),

    total_long_distance_charges NUMERIC(12,2)
        NOT NULL CHECK (total_long_distance_charges >= 0),

    total_revenue NUMERIC(12,2)
        NOT NULL CHECK (total_revenue >= 0),

    source_file_name VARCHAR(255) NOT NULL,
    ingested_at TIMESTAMP NOT NULL,
    transformed_at TIMESTAMP NOT NULL,

    core_loaded_at TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_services_customer
        FOREIGN KEY (customer_id)
        REFERENCES core.customer(customer_id),

    CONSTRAINT chk_internet_type
        CHECK (
            (internet_service = FALSE AND internet_type IS NULL)
            OR
            (internet_service = TRUE AND internet_type IS NOT NULL)
        )
);

CREATE TABLE core.customer_status (
    status_id VARCHAR(20) PRIMARY KEY,

    customer_id VARCHAR(20)
        NOT NULL UNIQUE,

    quarter VARCHAR(10) NOT NULL,

    satisfaction_score INTEGER NOT NULL
        CHECK (satisfaction_score BETWEEN 1 AND 5),

    customer_status VARCHAR(30) NOT NULL,

    churned BOOLEAN NOT NULL,

    churn_score INTEGER NOT NULL
        CHECK (churn_score BETWEEN 0 AND 100),

    cltv INTEGER NOT NULL
        CHECK (cltv >= 0),

    churn_category VARCHAR(50),
    churn_reason VARCHAR(150),

    source_file_name VARCHAR(255) NOT NULL,
    ingested_at TIMESTAMP NOT NULL,
    transformed_at TIMESTAMP NOT NULL,

    core_loaded_at TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_status_customer
        FOREIGN KEY (customer_id)
        REFERENCES core.customer(customer_id),

    CONSTRAINT chk_churn_details
        CHECK (
            (
                churned = TRUE
                AND churn_category IS NOT NULL
                AND churn_reason IS NOT NULL
            )
            OR
            (
                churned = FALSE
                AND churn_category IS NULL
                AND churn_reason IS NULL
            )
        )
);