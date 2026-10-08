-- Run in BigQuery to inspect the public sample before trusting monetary metrics.
-- event_date is the GA4 property date; all warehouse reporting uses UTC event_timestamp.
SELECT
  MIN(_TABLE_SUFFIX) AS first_table,
  MAX(_TABLE_SUFFIX) AS last_table,
  COUNT(*) AS events,
  COUNTIF(user_pseudo_id IS NULL OR user_pseudo_id = '') AS missing_user_id,
  COUNTIF((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id' LIMIT 1) IS NULL) AS missing_session_id,
  COUNTIF(event_name = 'purchase') AS purchase_events,
  COUNTIF(event_name = 'purchase' AND NULLIF(ecommerce.transaction_id, '') IS NULL) AS purchases_without_transaction,
  COUNTIF(event_name = 'purchase' AND ecommerce.purchase_revenue IS NULL) AS purchases_without_revenue,
  COUNTIF(event_name = 'purchase' AND ARRAY_LENGTH(items) = 0) AS purchases_without_items,
  COUNTIF(event_name = 'purchase' AND ecommerce.purchase_revenue IS NOT NULL
    AND ABS(ecommerce.purchase_revenue - (SELECT SUM(SAFE_CAST(i.price AS FLOAT64) * COALESCE(i.quantity, 1)) FROM UNNEST(items) i)) > 0.01
  ) AS purchase_item_mismatches
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131';
