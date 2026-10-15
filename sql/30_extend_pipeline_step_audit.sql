
-- ============================================================
-- TELCO CUSTOMER 360 - EXTEND PIPELINE STEP AUDIT
-- File: 30_extend_pipeline_step_audit.sql
--
-- Purpose:
--   - Track actual inserted, updated and unchanged records
--   - Improve pipeline monitoring and audit accuracy
-- ============================================================


ALTER TABLE audit.pipeline_step

ADD COLUMN IF NOT EXISTS
    rows_inserted INTEGER,

ADD COLUMN IF NOT EXISTS
    rows_updated INTEGER,

ADD COLUMN IF NOT EXISTS
    rows_unchanged INTEGER;