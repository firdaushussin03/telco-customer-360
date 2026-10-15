
-- ============================================================
-- TELCO CUSTOMER 360 - REMOVE SYNTHETIC BILLING TEST DATA
-- File: 55_cleanup_billing_test_records.sql
--
-- Keep original RAW records and audit history.
-- Remove only the three synthetic RAW versions.
-- Remove affected CORE records for later reprocessing.
-- ============================================================

BEGIN;

LOCK TABLE
    raw.billing_transactions,
    core.billing_transactions
IN SHARE ROW EXCLUSIVE MODE;

DO $$
DECLARE
    deleted_raw INTEGER;
    deleted_core INTEGER;
BEGIN

    -- 1. Verify that backups exist and contain expected rows.
    IF (SELECT COUNT(*) FROM audit.step52_raw_billing_backup) <> 5
       OR (SELECT COUNT(*) FROM audit.step52_core_billing_backup) <> 3
       OR (SELECT COUNT(*) FROM audit.step52_watermark_backup) <> 1
    THEN
        RAISE EXCEPTION 'Backup verification failed.';
    END IF;

    -- 2. Verify the current RAW history.
    IF (
        SELECT COUNT(*)
        FROM raw.billing_transactions
        WHERE bill_id IN (
            'BTEST-RECOVERY-001',
            'B202601-0215-BQKGS',
            'B202601-0420-BWTPW'
        )
    ) <> 5
    THEN
        RAISE EXCEPTION 'Unexpected RAW history.';
    END IF;

    -- 3. Verify current CORE records.
    IF (
        SELECT COUNT(*)
        FROM core.billing_transactions
        WHERE bill_id IN (
            'BTEST-RECOVERY-001',
            'B202601-0215-BQKGS',
            'B202601-0420-BWTPW'
        )
    ) <> 3
    THEN
        RAISE EXCEPTION 'Unexpected CORE records.';
    END IF;

    -- 4. Verify the checkpoint has not changed.
    IF (
        SELECT COUNT(*)
        FROM audit.pipeline_watermark
        WHERE pipeline_name = 'telco_customer_360'
          AND source_name = 'billing_transactions'
          AND last_watermark = TIMESTAMP '2026-06-08'
    ) <> 1
    THEN
        RAISE EXCEPTION 'Watermark changed. Stop cleanup.';
    END IF;

    -- 5. Remove only the synthetic RAW versions.
    DELETE FROM raw.billing_transactions
    WHERE
        (
            bill_id = 'BTEST-RECOVERY-001'
            AND payment_status = 'Paid'
            AND updated_at = TIMESTAMP '2026-01-03'
            AND source_file_name = 'billing_recovery_corrected.csv'
        )
        OR
        (
            bill_id = 'B202601-0215-BQKGS'
            AND payment_status = 'Paid'
            AND updated_at = TIMESTAMP '2026-03-02'
            AND source_file_name = 'billing_existing_corrected.csv'
        )
        OR
        (
            bill_id = 'B202601-0420-BWTPW'
            AND payment_status = 'Paid'
            AND updated_at = TIMESTAMP '2026-06-08'
            AND source_file_name = 'billing_newer_corrected.csv'
        );

    GET DIAGNOSTICS deleted_raw = ROW_COUNT;

    IF deleted_raw <> 3 THEN
        RAISE EXCEPTION
            'Expected 3 RAW deletions, got %.', deleted_raw;
    END IF;

    -- 6. Remove CORE test records.
    -- The normal pipeline will restore the two real bills.
    DELETE FROM core.billing_transactions
    WHERE
        (
            bill_id = 'BTEST-RECOVERY-001'
            AND payment_status = 'Paid'
            AND updated_at = TIMESTAMP '2026-01-03'
        )
        OR
        (
            bill_id = 'B202601-0215-BQKGS'
            AND payment_status = 'Paid'
            AND updated_at = TIMESTAMP '2026-03-02'
        )
        OR
        (
            bill_id = 'B202601-0420-BWTPW'
            AND payment_status = 'Paid'
            AND updated_at = TIMESTAMP '2026-06-08'
        );

    GET DIAGNOSTICS deleted_core = ROW_COUNT;

    IF deleted_core <> 3 THEN
        RAISE EXCEPTION
            'Expected 3 CORE deletions, got %.', deleted_core;
    END IF;

    -- 7. Confirm only original Pending RAW versions remain.
    IF (
        SELECT COUNT(*)
        FROM raw.billing_transactions
        WHERE
            (
                bill_id = 'B202601-0215-BQKGS'
                OR bill_id = 'B202601-0420-BWTPW'
            )
            AND payment_status = 'Pending'
            AND updated_at = TIMESTAMP '2026-01-01'
            AND source_file_name = 'billing_transactions.csv'
    ) <> 2
    THEN
        RAISE EXCEPTION 'Original Pending versions not found.';
    END IF;

    RAISE NOTICE 'RAW deleted: %', deleted_raw;
    RAISE NOTICE 'CORE deleted: %', deleted_core;
    RAISE NOTICE 'Cleanup successful. Rebuild required.';

END $$;

COMMIT;
