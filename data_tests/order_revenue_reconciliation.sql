-- GA4's obfuscated sample may fail; investigate rather than silently coerce.
WITH item_totals AS (
  SELECT transaction_id, SUM(item_amount) AS item_total,
    COUNT(*) AS item_count, COUNTIF(item_amount IS NULL) AS missing_amounts
  FROM {{ ref('fct_order_items') }} GROUP BY transaction_id
)
SELECT o.transaction_id, o.amount, i.item_total
FROM {{ ref('fct_orders') }} o JOIN item_totals i USING (transaction_id)
WHERE o.amount IS NOT NULL AND i.item_count > 0 AND i.missing_amounts = 0
  AND ABS(o.amount - i.item_total) > 0.01
