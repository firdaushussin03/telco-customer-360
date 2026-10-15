-- ============================================================
-- TELCO CUSTOMER 360 - RESOLVE BILLING RECOVERY
-- File: 43_resolve_billing_recovery.sql
-- ============================================================

UPDATE audit.billing_quarantine q

SET
    status = 'RESOLVED',

    resolved_at = CURRENT_TIMESTAMP,

    resolution_note =
        'Corrected billing record was recovered into RAW '
        || 'despite having an updated_at older than the watermark. '
        || 'Verified successful processing into CORE. '
        || 'Watermark remained unchanged.'

WHERE q.quarantine_id = 4

  AND q.bill_id = 'BTEST-RECOVERY-001'

  AND q.status = 'OPEN'

  -- Only resolve if the corrected RAW record exists.
  AND EXISTS (
      SELECT 1
      FROM raw.billing_transactions r
      WHERE r.bill_id = q.bill_id
        AND r.updated_at = TIMESTAMP '2026-01-03'
        AND r.source_file_name = 'billing_recovery_corrected.csv'
  )

  -- Only resolve if CORE contains the recovered bill.
  AND EXISTS (
      SELECT 1
      FROM core.billing_transactions c
      WHERE c.bill_id = q.bill_id
        AND c.updated_at = TIMESTAMP '2026-01-03'
        AND c.payment_status = 'Paid'
  )

RETURNING
    quarantine_id,
    bill_id,
    status,
    resolved_at,
    resolution_note;