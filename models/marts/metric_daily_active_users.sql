SELECT event_date AS date, COUNT(DISTINCT user_id) AS active_users
FROM {{ ref('fct_events') }} WHERE user_id IS NOT NULL
GROUP BY event_date
