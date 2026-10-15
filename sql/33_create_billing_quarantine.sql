
-- ============================================================
-- TELCO CUSTOMER 360 - BILLING QUARANTINE TABLE
-- File: 33_create_billing_quarantine.sql
--
-- Purpose:
--   - Store rejected billing source records
--   - Keep the original record for investigation
--   - Record why validation failed
-- ============================================================

CREATE TABLE IF NOT EXISTS audit.billing_quarantine (

    quarantine_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    bill_id VARCHAR(30),

    customer_id VARCHAR(20),

    source_file_name VARCHAR(255) NOT NULL,

    source_row_number INTEGER,

    raw_record JSONB NOT NULL,

    rejection_reason TEXT NOT NULL,

    detected_at TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(20)
        NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'RESOLVED'))

);
