-- Run in the US region after ga4_sandbox_views.sql.
-- Each SELECT returns a separate result set in BigQuery Studio.

SELECT
  COUNT(*) AS events,
  COUNT(DISTINCT event_id) AS distinct_event_ids,
  COUNTIF(event_name = 'purchase') AS purchase_events,
  COUNTIF(event_name = 'purchase' AND transaction_id IS NOT NULL) AS purchases_with_transaction_id
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events`;

SELECT
  (SELECT COUNT(*) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_orders`) AS orders,
  (SELECT COUNT(*) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_order_items`) AS order_items,
  (SELECT COUNT(*) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_dim_users`) AS users,
  (SELECT COUNT(*) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_dim_dates`) AS utc_dates,
  (SELECT COUNT(*) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_metric_daily_active_users`) AS dau_dates,
  (SELECT COUNT(*) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_metric_week1_retention`) AS cohort_weeks,
  (SELECT SUM(viewed_sessions) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_metric_session_funnel`) AS sessions_with_item_view;

SELECT
  (SELECT COUNT(*) - COUNT(DISTINCT event_id) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_events`) AS duplicate_event_ids,
  (SELECT COUNT(*) - COUNT(DISTINCT transaction_id) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_orders`) AS duplicate_order_ids,
  (SELECT COUNT(*) - COUNT(DISTINCT order_item_id) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_order_items`) AS duplicate_item_ids,
  (SELECT COUNT(*) FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_order_items` i
   LEFT JOIN `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_orders` o
   USING (transaction_id) WHERE o.transaction_id IS NULL) AS orphan_items;

WITH item_totals AS (
  SELECT transaction_id, SUM(item_amount) AS item_amount,
    COUNTIF(item_amount IS NULL) AS missing_item_amounts,
    COUNT(*) AS item_count
  FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_order_items`
  GROUP BY transaction_id
)
SELECT
  COUNTIF(i.item_count IS NULL) AS orders_without_items,
  COUNTIF(o.amount IS NULL) AS orders_without_revenue,
  COUNTIF(o.amount IS NOT NULL AND i.missing_item_amounts = 0
    AND ABS(o.amount - i.item_amount) <= 0.01) AS revenue_matches,
  COUNTIF(o.amount IS NOT NULL AND i.missing_item_amounts = 0
    AND ABS(o.amount - i.item_amount) > 0.01) AS revenue_mismatches
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_fct_orders` o
LEFT JOIN item_totals i USING (transaction_id);
