
-- ============================================================
-- TELCO CUSTOMER 360 - TEST DATA CLEANUP BACKUP
-- File: 54_backup_billing_cleanup.sql
--
-- Purpose:
--   - Back up the three test bills from RAW and CORE
--   - Preserve the current billing watermark
--   - Do not modify active warehouse data
-- ============================================================

BEGIN;


-- ============================================================
-- 1. BACK UP RAW BILLING HISTORY
-- ============================================================

CREATE TABLE audit.step52_raw_billing_backup AS

SELECT *
FROM raw.billing_transactions

WHERE bill_id IN (
    'BTEST-RECOVERY-001',
    'B202601-0215-BQKGS',
    'B202601-0420-BWTPW'
);


-- ============================================================
-- 2. BACK UP CURRENT CORE BILLING RECORDS
-- ============================================================

CREATE TABLE audit.step52_core_billing_backup AS

SELECT *
FROM core.billing_transactions

WHERE bill_id IN (
    'BTEST-RECOVERY-001',
    'B202601-0215-BQKGS',
    'B202601-0420-BWTPW'
);


-- ============================================================
-- 3. BACK UP THE BILLING WATERMARK
-- ============================================================

CREATE TABLE audit.step52_watermark_backup AS

SELECT *
FROM audit.pipeline_watermark

WHERE pipeline_name = 'telco_customer_360'
  AND source_name = 'billing_transactions';


COMMIT;
