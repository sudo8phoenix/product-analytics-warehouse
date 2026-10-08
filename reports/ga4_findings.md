# GA4 Sandbox findings

Measured on 2026-10-09 in the US BigQuery Sandbox project `gen-lang-client-0195528254`, using the deployed `ga4_` views over the public sample dated 2020-11-01 through 2021-01-31 (UTC). The combined query completed as job `job_SavmxWMNo_3A3yiQo5S8JNOgb3Y_`.

## 1. Session funnel

```sql
SELECT SUM(viewed_sessions) AS viewed_sessions,
  SUM(cart_sessions) AS cart_sessions,
  SUM(checkout_sessions) AS checkout_sessions,
  SUM(purchase_sessions) AS purchase_sessions
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_metric_session_funnel`;
```

**Observed result:** 77,020 viewed, 15,167 carted, 5,416 reached checkout, and 2,834 purchased. The largest step loss is view to cart: 61,853 sessions, or 80.31% of viewed sessions.

**Limitation:** The funnel requires an identified user and GA4 session ID, ordered events, and a transaction ID for the purchase step. It groups a session under the date of its first item view, even when later stages occur on subsequent dates. The sample is obfuscated; this is descriptive, not causal.

**Next action:** Segment the view-to-cart transition by item and device, then inspect item availability and cart instrumentation before proposing a product change.

## 2. Daily active users

```sql
SELECT COUNT(*) AS dates, MIN(active_users) AS min_dau,
  MAX(active_users) AS max_dau, ROUND(AVG(active_users), 1) AS mean_dau
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_metric_daily_active_users`;
```

**Observed result:** Across 92 UTC dates, DAU ranged from 309 to 1,357, with a mean of 790.5.

**Limitation:** DAU counts distinct `user_pseudo_id` values with one of the four modeled ecommerce events. It is not GA4's full active-user definition, and the first and last calendar dates may be partial.

**Next action:** Compare the daily series with the full GA4 export's activity definition and investigate sharp changes by weekday and event type.

## 3. Week-one retention

```sql
SELECT COUNT(*) AS complete_cohorts,
  SUM(cohort_users) AS cohort_users,
  SUM(returned_users) AS returned_users,
  ROUND(100 * SAFE_DIVIDE(SUM(returned_users), SUM(cohort_users)), 2) AS weighted_return_pct
FROM `gen-lang-client-0195528254.product_analytics_warehouse.ga4_metric_week1_retention`
WHERE cohort_week BETWEEN DATE '2020-11-02' AND DATE '2021-01-18';
```

**Observed result:** The 12 cohorts with a fully observed following week contain 55,878 users; 2,515 returned in the next Monday–Sunday UTC week, a weighted return rate of 4.50%.

**Limitation:** Cohorts use the first observed modeled ecommerce event, not a user's true acquisition date. The first and final cohort weeks are excluded because their observation windows are incomplete. Obfuscation and missing activity outside the four modeled events can bias the rate.

**Next action:** Repeat the cohort calculation on a complete event export with a longer observation window and segment by first interaction and acquisition source.
