
-- ============================================================
-- TELCO CUSTOMER 360 - RUN 19 BILLING REPAIR
-- File: 37_repair_run19_billing.sql
--
-- Purpose:
--   1. Remove the incorrect Excel-affected RAW version
--   2. Restore CORE using the correct RAW version
--   3. Repair the billing watermark
--
-- Prerequisite:
--   audit.run19_billing_repair_backup contains 5 rows
-- ============================================================

BEGIN;

DO $$
DECLARE
    deleted_rows INTEGER;
    updated_core_rows INTEGER;
    updated_watermark_rows INTEGER;

BEGIN

    -- Ensure the backup exists and has the expected rows.
    IF (
        SELECT COUNT(*)
        FROM audit.run19_billing_repair_backup
    ) <> 5 THEN
        RAISE EXCEPTION 'Repair backup verification failed.';
    END IF;


    -- 1. Remove only the incorrect July 6 RAW version.
    DELETE FROM raw.billing_transactions
    WHERE bill_id = 'B202601-4385-GZQXV'
      AND created_at = TIMESTAMP '2026-02-01'
      AND updated_at = TIMESTAMP '2026-07-06'
      AND ingested_at = TIMESTAMP '2026-10-09 17:12:47.136246';

    GET DIAGNOSTICS deleted_rows = ROW_COUNT;

    IF deleted_rows <> 1 THEN
        RAISE EXCEPTION
            'Expected to delete 1 RAW row, deleted %.',
            deleted_rows;
    END IF;


    -- 2. Restore CORE from the correct RAW version.
    UPDATE core.billing_transactions c
    SET
        customer_id = r.customer_id,
        billing_date = r.billing_date,
        base_monthly_charge = r.base_monthly_charge,
        long_distance_charge = r.long_distance_charge,
        extra_data_charge = r.extra_data_charge,
        discount_amount = r.discount_amount,
        total_amount = r.total_amount,
        payment_method = r.payment_method,
        payment_status = r.payment_status,
        created_at = r.created_at,
        updated_at = r.updated_at,
        source_file_name = r.source_file_name,
        ingested_at = r.ingested_at,
        core_updated_at = CURRENT_TIMESTAMP
    FROM raw.billing_transactions r
    WHERE c.bill_id = 'B202601-4385-GZQXV'
      AND c.updated_at = TIMESTAMP '2026-07-06'
      AND r.bill_id = c.bill_id
      AND r.created_at = TIMESTAMP '2026-01-02'
      AND r.updated_at = TIMESTAMP '2026-06-07';

    GET DIAGNOSTICS updated_core_rows = ROW_COUNT;

    IF updated_core_rows <> 1 THEN
        RAISE EXCEPTION
            'Expected to repair 1 CORE row, repaired %.',
            updated_core_rows;
    END IF;


    -- 3. Recalculate the watermark from the remaining RAW data.
    UPDATE audit.pipeline_watermark
    SET
        last_watermark = (
            SELECT MAX(updated_at)
            FROM raw.billing_transactions
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE pipeline_name = 'telco_customer_360'
      AND source_name = 'billing_transactions'
      AND last_watermark = TIMESTAMP '2026-07-06';

    GET DIAGNOSTICS updated_watermark_rows = ROW_COUNT;

    IF updated_watermark_rows <> 1 THEN
        RAISE EXCEPTION
            'Expected to repair 1 watermark row, repaired %.',
            updated_watermark_rows;
    END IF;


    -- 4. Verify the corrected watermark.
    IF (
        SELECT last_watermark
        FROM audit.pipeline_watermark
        WHERE pipeline_name = 'telco_customer_360'
          AND source_name = 'billing_transactions'
    ) <> TIMESTAMP '2026-06-07' THEN

        RAISE EXCEPTION 'Corrected watermark is not June 7.';
    END IF;

    RAISE NOTICE 'RAW deleted: %, CORE repaired: %, Watermark repaired: %',
        deleted_rows,
        updated_core_rows,
        updated_watermark_rows;

END $$;

COMMIT;
