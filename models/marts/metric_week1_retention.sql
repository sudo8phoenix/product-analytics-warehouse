WITH activity AS (
  SELECT DISTINCT user_id, DATE_TRUNC(event_date, WEEK(MONDAY)) AS active_week
  FROM {{ ref('fct_events') }} WHERE user_id IS NOT NULL
), cohorts AS (
  SELECT user_id, DATE_TRUNC(DATE(first_seen_at), WEEK(MONDAY)) AS cohort_week
  FROM {{ ref('dim_users') }}
)
SELECT c.cohort_week, COUNT(DISTINCT c.user_id) AS cohort_users,
  COUNT(DISTINCT a.user_id) AS returned_users,
  SAFE_DIVIDE(COUNT(DISTINCT a.user_id), COUNT(DISTINCT c.user_id)) AS week1_return_rate
FROM cohorts c LEFT JOIN activity a ON a.user_id = c.user_id
  AND a.active_week = DATE_ADD(c.cohort_week, INTERVAL 1 WEEK)
GROUP BY c.cohort_week
