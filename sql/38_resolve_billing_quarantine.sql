
-- ============================================================
-- TELCO CUSTOMER 360 - RESOLVE QUARANTINE ID 3
-- File: 38_resolve_billing_quarantine.sql
--
-- Purpose:
--   Close a quarantine case after confirming the original
--   valid billing record already exists in RAW and CORE.
-- ============================================================

UPDATE audit.billing_quarantine

SET
    status = 'RESOLVED',

    resolved_at = CURRENT_TIMESTAMP,

    resolution_note =
        'Original CSV restored after Excel date formatting issue. '
        || 'Verified that the valid bill already exists in RAW '
        || 'and CORE. No additional ingestion was required.'

WHERE quarantine_id = 3
  AND bill_id = 'B202601-7495-OOKFY'
  AND status = 'OPEN';
