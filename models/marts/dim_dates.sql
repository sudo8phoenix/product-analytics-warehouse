SELECT date, DATE_TRUNC(date, WEEK(MONDAY)) AS week_start
FROM UNNEST(GENERATE_DATE_ARRAY(
  (SELECT MIN(event_date) FROM {{ ref('fct_events') }}),
  (SELECT MAX(event_date) FROM {{ ref('fct_events') }})
)) AS date
