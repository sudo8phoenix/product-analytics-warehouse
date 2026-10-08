SELECT transaction_id, event_id, event_ts AS order_ts, event_date AS order_date,
  user_id, session_id, purchase_revenue AS amount, currency
FROM {{ ref('stg_ga4_events') }}
WHERE event_name = 'purchase' AND transaction_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id
  ORDER BY event_ts DESC, event_id DESC) = 1
