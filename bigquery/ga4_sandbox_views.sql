-- Generated from models/ by python -m warehouse.ga4_sandbox

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_stg_ga4_events` AS
WITH source AS (
  SELECT t.*,
    TO_HEX(SHA256(TO_JSON_STRING(t))) AS source_hash,
    ROW_NUMBER() OVER (
      PARTITION BY TO_JSON_STRING(t) ORDER BY event_timestamp
    ) AS duplicate_ordinal
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*` t
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
), canonical AS (
  SELECT
    CONCAT('ga4:', source_hash, ':', CAST(duplicate_ordinal AS STRING)) AS event_id,
    TIMESTAMP_MICROS(event_timestamp) AS event_ts,
    DATE(TIMESTAMP_MICROS(event_timestamp)) AS event_date,
    NULLIF(user_pseudo_id, '') AS user_id,
    CAST((SELECT value.int_value FROM UNNEST(event_params)
      WHERE key = 'ga_session_id' LIMIT 1) AS STRING) AS session_id,
    event_name,
    NULLIF(ecommerce.transaction_id, '') AS transaction_id,
    SAFE_CAST(ecommerce.purchase_revenue AS NUMERIC) AS purchase_revenue,
    (SELECT COALESCE(value.double_value, CAST(value.int_value AS FLOAT64),
      SAFE_CAST(value.string_value AS FLOAT64)) FROM UNNEST(event_params)
      WHERE key = 'value' LIMIT 1) AS event_value,
    (SELECT value.string_value FROM UNNEST(event_params)
      WHERE key = 'currency' LIMIT 1) AS currency,
    NULLIF(traffic_source.source, '') AS acquisition_channel,
    items
  FROM source
)
SELECT * FROM canonical
WHERE event_name IN ('view_item', 'add_to_cart', 'begin_checkout', 'purchase');

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events` AS
SELECT event_id, event_ts, event_date, user_id, session_id, event_name,
  transaction_id, purchase_revenue, event_value, currency, acquisition_channel
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_stg_ga4_events`;

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_orders` AS
SELECT transaction_id, event_id, event_ts AS order_ts, event_date AS order_date,
  user_id, session_id, purchase_revenue AS amount, currency
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_stg_ga4_events`
WHERE event_name = 'purchase' AND transaction_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id
  ORDER BY event_ts DESC, event_id DESC) = 1;

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_order_items` AS
SELECT CONCAT(o.event_id, ':', CAST(item_offset AS STRING)) AS order_item_id,
  o.transaction_id, o.event_id, item_offset,
  NULLIF(item.item_id, '') AS product_id,
  SAFE_CAST(item.quantity AS INT64) AS quantity,
  SAFE_CAST(item.price AS NUMERIC) AS unit_price,
  SAFE_CAST(item.price AS NUMERIC) * SAFE_CAST(item.quantity AS NUMERIC) AS item_amount,
  o.currency, o.order_date
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_orders` o
JOIN `gen-lang-client-0195528254.product_analytics_warehouse.ga4_stg_ga4_events` e ON e.event_id = o.event_id
CROSS JOIN UNNEST(e.items) AS item WITH OFFSET AS item_offset;

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_dim_users` AS
SELECT user_id, MIN(event_ts) AS first_seen_at,
  ARRAY_AGG(acquisition_channel IGNORE NULLS ORDER BY event_ts, event_id LIMIT 1)[SAFE_OFFSET(0)] AS acquisition_channel
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events`
WHERE user_id IS NOT NULL
GROUP BY user_id;

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_dim_products` AS
SELECT product_id FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_order_items`
WHERE product_id IS NOT NULL GROUP BY product_id;

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_dim_dates` AS
SELECT date, DATE_TRUNC(date, WEEK(MONDAY)) AS week_start
FROM UNNEST(GENERATE_DATE_ARRAY(
  (SELECT MIN(event_date) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events`),
  (SELECT MAX(event_date) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events`)
)) AS date;

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_metric_daily_active_users` AS
SELECT event_date AS date, COUNT(DISTINCT user_id) AS active_users
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events` WHERE user_id IS NOT NULL
GROUP BY event_date;

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_metric_week1_retention` AS
WITH activity AS (
  SELECT DISTINCT user_id, DATE_TRUNC(event_date, WEEK(MONDAY)) AS active_week
  FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events` WHERE user_id IS NOT NULL
), cohorts AS (
  SELECT user_id, DATE_TRUNC(DATE(first_seen_at), WEEK(MONDAY)) AS cohort_week
  FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_dim_users`
)
SELECT c.cohort_week, COUNT(DISTINCT c.user_id) AS cohort_users,
  COUNT(DISTINCT a.user_id) AS returned_users,
  SAFE_DIVIDE(COUNT(DISTINCT a.user_id), COUNT(DISTINCT c.user_id)) AS week1_return_rate
FROM cohorts c LEFT JOIN activity a ON a.user_id = c.user_id
  AND a.active_week = DATE_ADD(c.cohort_week, INTERVAL 1 WEEK)
GROUP BY c.cohort_week;

CREATE OR REPLACE VIEW `gen-lang-client-0195528254.product_analytics_warehouse.ga4_metric_session_funnel` AS
WITH views AS (
  SELECT user_id, session_id, MIN(event_ts) AS viewed_at
  FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events`
  WHERE event_name = 'view_item' AND user_id IS NOT NULL AND session_id IS NOT NULL
  GROUP BY user_id, session_id
), carts AS (
  SELECT e.user_id, e.session_id, MIN(e.event_ts) AS carted_at
  FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events` e JOIN views v USING (user_id, session_id)
  WHERE e.event_name = 'add_to_cart' AND e.event_ts >= v.viewed_at
  GROUP BY e.user_id, e.session_id
), checkouts AS (
  SELECT e.user_id, e.session_id, MIN(e.event_ts) AS checkout_at
  FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events` e JOIN carts c USING (user_id, session_id)
  WHERE e.event_name = 'begin_checkout' AND e.event_ts >= c.carted_at
  GROUP BY e.user_id, e.session_id
), purchases AS (
  SELECT e.user_id, e.session_id, MIN(e.event_ts) AS purchased_at
  FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events` e JOIN checkouts c USING (user_id, session_id)
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
GROUP BY date;
