
-- ============================================================
-- TELCO CUSTOMER 360 - RESOLVE EXISTING BILL RECOVERY
-- File: 48_resolve_existing_bill_recovery.sql
--
-- Purpose:
--   Mark quarantine ID 5 as RESOLVED after verifying
--   the corrected billing update reached RAW and CORE.
-- ============================================================

UPDATE audit.billing_quarantine q

SET
    status = 'RESOLVED',

    resolved_at = CURRENT_TIMESTAMP,

    resolution_note =
        'Corrected existing bill from Pending to Paid. '
        || 'Recovered the newer version into RAW despite '
        || 'its updated_at being older than the watermark. '
        || 'Verified STAGING and CORE contain the Paid version. '
        || 'Original Pending version preserved in RAW. '
        || 'Duplicate prevention tested successfully.'

WHERE q.quarantine_id = 5

  AND q.bill_id = 'B202601-0215-BQKGS'

  AND q.status = 'OPEN'

  -- Verify corrected version exists in RAW.
  AND EXISTS (
      SELECT 1
      FROM raw.billing_transactions r
      WHERE r.bill_id = q.bill_id
        AND r.payment_status = 'Paid'
        AND r.updated_at = TIMESTAMP '2026-03-02'
        AND r.source_file_name = 'billing_existing_corrected.csv'
  )

  -- Verify STAGING contains the corrected version.
  AND EXISTS (
      SELECT 1
      FROM staging.billing_transactions s
      WHERE s.bill_id = q.bill_id
        AND s.payment_status = 'Paid'
        AND s.updated_at = TIMESTAMP '2026-03-02'
  )

  -- Verify CORE contains the corrected version.
  AND EXISTS (
      SELECT 1
      FROM core.billing_transactions c
      WHERE c.bill_id = q.bill_id
        AND c.payment_status = 'Paid'
        AND c.updated_at = TIMESTAMP '2026-03-02'
  )

RETURNING
    quarantine_id,
    bill_id,
    status,
    resolved_at,
    resolution_note;
