
-- ============================================================
-- TELCO CUSTOMER 360 - PREVIEW BILLING UPSERT ACTIONS
-- File: 31_preview_billing_upsert_actions.sql
--
-- Purpose:
--   - Identify billing rows requiring INSERT
--   - Identify billing rows requiring UPDATE
--   - Identify unchanged billing rows
--   - Detect missing identifiers or update timestamps
-- ============================================================

WITH classified_bills AS (

    SELECT
        s.bill_id,

        CASE
            WHEN s.bill_id IS NULL
              OR s.updated_at IS NULL
                THEN 'INVALID'

            WHEN c.bill_id IS NULL
                THEN 'INSERT'

            WHEN s.updated_at > c.updated_at
                THEN 'UPDATE'

            ELSE 'UNCHANGED'
        END AS action_type

    FROM staging.billing_transactions s

    LEFT JOIN core.billing_transactions c
        ON s.bill_id = c.bill_id
)

SELECT
    COUNT(*) AS staging_rows,

    COUNT(*) FILTER (
        WHERE action_type = 'INSERT'
    ) AS rows_to_insert,

    COUNT(*) FILTER (
        WHERE action_type = 'UPDATE'
    ) AS rows_to_update,

    COUNT(*) FILTER (
        WHERE action_type = 'UNCHANGED'
    ) AS rows_unchanged,

    COUNT(*) FILTER (
        WHERE action_type = 'INVALID'
    ) AS invalid_rows

FROM classified_bills;
