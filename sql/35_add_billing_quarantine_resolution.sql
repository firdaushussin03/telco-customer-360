
-- ============================================================
-- TELCO CUSTOMER 360 - QUARANTINE RESOLUTION TRACKING
-- File: 35_add_billing_quarantine_resolution.sql
--
-- Purpose:
--   - Track when quarantined records are resolved
--   - Record notes explaining how issues were resolved
-- ============================================================

ALTER TABLE audit.billing_quarantine
ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP;

ALTER TABLE audit.billing_quarantine
ADD COLUMN IF NOT EXISTS resolution_note TEXT;