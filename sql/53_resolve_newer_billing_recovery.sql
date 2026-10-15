
-- ============================================================
-- TELCO CUSTOMER 360
-- Resolve newer-than-watermark billing recovery
-- ============================================================

UPDATE audit.billing_quarantine q

SET
    status = 'RESOLVED',

    resolved_at = CURRENT_TIMESTAMP,

    resolution_note =
        'Corrected missing updated_at to 2026-06-08. '
        || 'Recovered Paid update through normal incremental '
        || 'ingestion. Verified RAW, STAGING and CORE. '
        || 'Watermark advanced from 2026-06-07 to 2026-06-08.'

WHERE q.quarantine_id = 6

  AND q.bill_id = 'B202601-0420-BWTPW'

  AND q.status = 'OPEN'

  AND q.source_file_name = 'billing_newer_invalid.csv'

  -- Confirm corrected version exists in RAW.
  AND EXISTS (
      SELECT 1
      FROM raw.billing_transactions r
      WHERE r.bill_id = q.bill_id
        AND r.payment_status = 'Paid'
        AND r.updated_at = TIMESTAMP '2026-06-08'
        AND r.source_file_name = 'billing_newer_corrected.csv'
  )

  -- Confirm STAGING is updated.
  AND EXISTS (
      SELECT 1
      FROM staging.billing_transactions s
      WHERE s.bill_id = q.bill_id
        AND s.payment_status = 'Paid'
        AND s.updated_at = TIMESTAMP '2026-06-08'
  )

  -- Confirm CORE is updated.
  AND EXISTS (
      SELECT 1
      FROM core.billing_transactions c
      WHERE c.bill_id = q.bill_id
        AND c.payment_status = 'Paid'
        AND c.updated_at = TIMESTAMP '2026-06-08'
  )

RETURNING
    quarantine_id,
    bill_id,
    status,
    resolved_at,
    resolution_note;
