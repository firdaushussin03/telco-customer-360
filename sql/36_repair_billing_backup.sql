CREATE TABLE IF NOT EXISTS audit.run19_billing_repair_backup AS

SELECT
    'RAW' AS data_layer,
    to_jsonb(r) AS record_snapshot,
    CURRENT_TIMESTAMP AS backed_up_at
FROM raw.billing_transactions r
WHERE r.bill_id = 'B202601-4385-GZQXV'

UNION ALL

SELECT
    'CORE',
    to_jsonb(c),
    CURRENT_TIMESTAMP
FROM core.billing_transactions c
WHERE c.bill_id = 'B202601-4385-GZQXV'

UNION ALL

SELECT
    'WATERMARK',
    to_jsonb(w),
    CURRENT_TIMESTAMP
FROM audit.pipeline_watermark w
WHERE w.pipeline_name = 'telco_customer_360'
  AND w.source_name = 'billing_transactions';


SELECT
    data_layer,
    COUNT(*) AS backed_up_rows
FROM audit.run19_billing_repair_backup
GROUP BY data_layer
ORDER BY data_layer;