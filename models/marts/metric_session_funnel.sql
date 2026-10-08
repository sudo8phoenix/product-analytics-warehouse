WITH views AS (
  SELECT user_id, session_id, MIN(event_ts) AS viewed_at
  FROM {{ ref('fct_events') }}
  WHERE event_name = 'view_item' AND user_id IS NOT NULL AND session_id IS NOT NULL
  GROUP BY user_id, session_id
), carts AS (
  SELECT e.user_id, e.session_id, MIN(e.event_ts) AS carted_at
  FROM {{ ref('fct_events') }} e JOIN views v USING (user_id, session_id)
  WHERE e.event_name = 'add_to_cart' AND e.event_ts >= v.viewed_at
  GROUP BY e.user_id, e.session_id
), checkouts AS (
  SELECT e.user_id, e.session_id, MIN(e.event_ts) AS checkout_at
  FROM {{ ref('fct_events') }} e JOIN carts c USING (user_id, session_id)
  WHERE e.event_name = 'begin_checkout' AND e.event_ts >= c.carted_at
  GROUP BY e.user_id, e.session_id
), purchases AS (
  SELECT e.user_id, e.session_id, MIN(e.event_ts) AS purchased_at
  FROM {{ ref('fct_events') }} e JOIN checkouts c USING (user_id, session_id)
  WHERE e.event_name = 'purchase' AND e.transaction_id IS NOT NULL
    AND e.event_ts >= c.checkout_at
  GROUP BY e.user_id, e.session_id
)
SELECT DATE(v.viewed_at) AS date,
  COUNT(*) AS viewed_sessions,
  COUNT(c.user_id) AS cart_sessions,
  COUNT(ch.user_id) AS checkout_sessions,
  COUNT(p.user_id) AS purchase_sessions
FROM views v
LEFT JOIN carts c USING (user_id, session_id)
LEFT JOIN checkouts ch USING (user_id, session_id)
LEFT JOIN purchases p USING (user_id, session_id)
GROUP BY date
