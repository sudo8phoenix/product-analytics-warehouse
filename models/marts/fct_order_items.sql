SELECT CONCAT(o.event_id, ':', CAST(item_offset AS STRING)) AS order_item_id,
  o.transaction_id, o.event_id, item_offset,
  NULLIF(item.item_id, '') AS product_id,
  SAFE_CAST(item.quantity AS INT64) AS quantity,
  SAFE_CAST(item.price AS NUMERIC) AS unit_price,
  SAFE_CAST(item.price AS NUMERIC) * SAFE_CAST(item.quantity AS NUMERIC) AS item_amount,
  o.currency, o.order_date
FROM {{ ref('fct_orders') }} o
JOIN {{ ref('stg_ga4_events') }} e ON e.event_id = o.event_id
CROSS JOIN UNNEST(e.items) AS item WITH OFFSET AS item_offset
