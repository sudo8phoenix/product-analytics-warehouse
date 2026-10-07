-- Replace PROJECT_ID before running. These should match the local full-data run.
SELECT
  (SELECT COUNT(*) FROM `PROJECT_ID.product_analytics_warehouse.raw_events`) AS raw_rows,
  (SELECT COUNT(*) FROM `PROJECT_ID.product_analytics_warehouse.fct_events`) AS event_rows,
  (SELECT COUNT(DISTINCT event_id) FROM `PROJECT_ID.product_analytics_warehouse.fct_events`) AS distinct_event_ids,
  (SELECT COUNT(*) FROM `PROJECT_ID.product_analytics_warehouse.fct_orders`) AS orders,
  (SELECT COUNT(*) FROM `PROJECT_ID.product_analytics_warehouse.dim_users`) AS visitors;

SELECT stage, visitors
FROM `PROJECT_ID.product_analytics_warehouse.metric_visitor_funnel`
ORDER BY stage_order;

SELECT cohort_week, cohort_users, returned_users, week_1_return_pct
FROM `PROJECT_ID.product_analytics_warehouse.metric_week1_retention`
WHERE cohort_week = DATE '2015-05-04';

SELECT date, active_visitors
FROM `PROJECT_ID.product_analytics_warehouse.metric_daily_active_users`
ORDER BY active_visitors DESC, date
LIMIT 1;
