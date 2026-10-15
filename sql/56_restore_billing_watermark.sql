
-- ============================================================
-- TELCO CUSTOMER 360 - RESTORE BILLING WATERMARK
-- File: 56_restore_billing_watermark.sql
--
-- Purpose:
--   Restore the watermark after controlled test cleanup.
--
-- Expected current watermark: 2026-06-08
-- Expected latest normal RAW update: 2026-06-07
-- ============================================================

BEGIN;

DO $$
DECLARE
    current_watermark TIMESTAMP;
    latest_raw_timestamp TIMESTAMP;
BEGIN

    -- 1. Get and lock the current watermark.
    SELECT last_watermark
    INTO current_watermark
    FROM audit.pipeline_watermark
    WHERE pipeline_name = 'telco_customer_360'
      AND source_name = 'billing_transactions'
    FOR UPDATE;

    -- 2. Verify the watermark has not changed.
    IF current_watermark IS DISTINCT FROM
       TIMESTAMP '2026-06-08 00:00:00'
    THEN
        RAISE EXCEPTION
            'Unexpected current watermark: %',
            current_watermark;
    END IF;

    -- 3. Check the latest normal-source RAW timestamp.
    SELECT MAX(updated_at)
    INTO latest_raw_timestamp
    FROM raw.billing_transactions
    WHERE source_file_name = 'billing_transactions.csv';

    IF latest_raw_timestamp IS DISTINCT FROM
       TIMESTAMP '2026-06-07 00:00:00'
    THEN
        RAISE EXCEPTION
            'Unexpected latest RAW timestamp: %',
            latest_raw_timestamp;
    END IF;

    -- 4. Confirm the synthetic versions were removed.
    IF EXISTS (
        SELECT 1
        FROM raw.billing_transactions
        WHERE bill_id = 'BTEST-RECOVERY-001'

           OR (
               bill_id = 'B202601-0215-BQKGS'
               AND updated_at = TIMESTAMP '2026-03-02'
           )

           OR (
               bill_id = 'B202601-0420-BWTPW'
               AND updated_at = TIMESTAMP '2026-06-08'
           )
    )
    THEN
        RAISE EXCEPTION
            'Synthetic billing records still exist in RAW.';
    END IF;

    -- 5. Restore the watermark.
    UPDATE audit.pipeline_watermark
    SET
        last_watermark = TIMESTAMP '2026-06-07 00:00:00',
        updated_at = CURRENT_TIMESTAMP
    WHERE pipeline_name = 'telco_customer_360'
      AND source_name = 'billing_transactions';

    RAISE NOTICE 'Watermark restored successfully.';
    RAISE NOTICE 'Previous watermark: %', current_watermark;
    RAISE NOTICE 'Restored watermark: 2026-06-07';

END $$;

COMMIT;
