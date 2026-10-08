SELECT o.transaction_id
FROM {{ ref('fct_orders') }} o
JOIN {{ ref('stg_ga4_events') }} e ON e.event_id = o.event_id
LEFT JOIN {{ ref('fct_order_items') }} i ON i.event_id = o.event_id
GROUP BY o.transaction_id, ARRAY_LENGTH(e.items)
HAVING COUNT(i.order_item_id) != ARRAY_LENGTH(e.items)
