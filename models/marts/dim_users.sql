SELECT user_id, MIN(event_ts) AS first_seen_at,
  ARRAY_AGG(acquisition_channel IGNORE NULLS ORDER BY event_ts, event_id LIMIT 1)[SAFE_OFFSET(0)] AS acquisition_channel
FROM {{ ref('fct_events') }}
WHERE user_id IS NOT NULL
GROUP BY user_id
