-- Replace PROJECT_ID with your Google Cloud project ID before running.
-- The source table is a load-job REPLACE of Retailrocket's events.csv.
-- Views are safe to rerun in BigQuery Sandbox (which does not support DML).

CREATE OR REPLACE VIEW `PROJECT_ID.product_analytics_warehouse.fct_events` AS
WITH numbered AS (
  SELECT
    `timestamp` AS timestamp_ms,
    CAST(visitorid AS STRING) AS user_id,
    CAST(event AS STRING) AS source_event,
    CAST(itemid AS STRING) AS product_id,
    CAST(transactionid AS STRING) AS transaction_id,
    ROW_NUMBER() OVER (
      PARTITION BY `timestamp`, visitorid, event, itemid, transactionid
      ORDER BY `timestamp`
    ) AS duplicate_ordinal
  FROM `PROJECT_ID.product_analytics_warehouse.raw_events`
)
SELECT
  CONCAT('rr:', TO_HEX(MD5(TO_JSON_STRING(STRUCT(
    timestamp_ms, user_id, source_event, product_id, transaction_id
  )))), ':', CAST(duplicate_ordinal AS STRING)) AS event_id,
  TIMESTAMP_MILLIS(SAFE_CAST(timestamp_ms AS INT64)) AS event_ts,
  DATE(TIMESTAMP_MILLIS(SAFE_CAST(timestamp_ms AS INT64))) AS event_date,
  user_id,
  CASE source_event
    WHEN 'view' THEN 'view_item'
    WHEN 'addtocart' THEN 'add_to_cart'
    WHEN 'transaction' THEN 'purchase'
  END AS event_name,
  product_id,
  transaction_id
FROM numbered;

CREATE OR REPLACE VIEW `PROJECT_ID.product_analytics_warehouse.fct_orders` AS
SELECT transaction_id, event_id, event_ts AS order_ts, event_date AS order_date, user_id
FROM `PROJECT_ID.product_analytics_warehouse.fct_events`
WHERE event_name = 'purchase' AND transaction_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY transaction_id ORDER BY event_ts DESC, event_id DESC
) = 1;

CREATE OR REPLACE VIEW `PROJECT_ID.product_analytics_warehouse.fct_order_items` AS
SELECT event_id AS order_item_id, transaction_id, product_id, user_id, event_ts
FROM `PROJECT_ID.product_analytics_warehouse.fct_events`
WHERE event_name = 'purchase' AND transaction_id IS NOT NULL;

CREATE OR REPLACE VIEW `PROJECT_ID.product_analytics_warehouse.dim_users` AS
SELECT user_id, MIN(event_ts) AS first_seen_at
FROM `PROJECT_ID.product_analytics_warehouse.fct_events`
WHERE user_id IS NOT NULL
GROUP BY user_id;

CREATE OR REPLACE VIEW `PROJECT_ID.product_analytics_warehouse.dim_products` AS
SELECT DISTINCT product_id
FROM `PROJECT_ID.product_analytics_warehouse.fct_events`
WHERE product_id IS NOT NULL;

CREATE OR REPLACE VIEW `PROJECT_ID.product_analytics_warehouse.dim_dates` AS
SELECT DISTINCT event_date AS date, DATE_TRUNC(event_date, WEEK(MONDAY)) AS week_start
FROM `PROJECT_ID.product_analytics_warehouse.fct_events`;

CREATE OR REPLACE VIEW `PROJECT_ID.product_analytics_warehouse.metric_daily_active_users` AS
SELECT event_date AS date, COUNT(DISTINCT user_id) AS active_visitors
FROM `PROJECT_ID.product_analytics_warehouse.fct_events`
WHERE user_id IS NOT NULL
GROUP BY event_date;

CREATE OR REPLACE VIEW `PROJECT_ID.product_analytics_warehouse.metric_week1_retention` AS
WITH cohorts AS (
  SELECT user_id, DATE_TRUNC(DATE(first_seen_at), WEEK(MONDAY)) AS cohort_week
  FROM `PROJECT_ID.product_analytics_warehouse.dim_users`
), activity AS (
  SELECT DISTINCT user_id, DATE_TRUNC(event_date, WEEK(MONDAY)) AS active_week
  FROM `PROJECT_ID.product_analytics_warehouse.fct_events`
  WHERE user_id IS NOT NULL
)
SELECT
  c.cohort_week,
  COUNT(DISTINCT c.user_id) AS cohort_users,
  COUNT(DISTINCT a.user_id) AS returned_users,
  ROUND(100 * SAFE_DIVIDE(COUNT(DISTINCT a.user_id), COUNT(DISTINCT c.user_id)), 2) AS week_1_return_pct
FROM cohorts c
LEFT JOIN activity a
  ON a.user_id = c.user_id
  AND a.active_week = DATE_ADD(c.cohort_week, INTERVAL 1 WEEK)
GROUP BY c.cohort_week;

CREATE OR REPLACE VIEW `PROJECT_ID.product_analytics_warehouse.metric_visitor_funnel` AS
WITH views AS (
  SELECT user_id, MIN(event_ts) AS viewed
  FROM `PROJECT_ID.product_analytics_warehouse.fct_events`
  WHERE event_name = 'view_item' AND user_id IS NOT NULL
  GROUP BY user_id
), carts AS (
  SELECT e.user_id, MIN(e.event_ts) AS carted
  FROM `PROJECT_ID.product_analytics_warehouse.fct_events` e
  JOIN views v ON e.user_id = v.user_id AND e.event_ts >= v.viewed
  WHERE e.event_name = 'add_to_cart'
  GROUP BY e.user_id
), purchases AS (
  SELECT e.user_id, MIN(e.event_ts) AS purchased
  FROM `PROJECT_ID.product_analytics_warehouse.fct_orders` o
  JOIN `PROJECT_ID.product_analytics_warehouse.fct_events` e ON e.event_id = o.event_id
  JOIN carts c ON e.user_id = c.user_id AND e.event_ts >= c.carted
  GROUP BY e.user_id
)
SELECT 'view_item' AS stage, COUNT(*) AS visitors, 1 AS stage_order FROM views
UNION ALL
SELECT 'add_to_cart', COUNT(*), 2 FROM carts
UNION ALL
SELECT 'purchase', COUNT(*), 3 FROM purchases;
