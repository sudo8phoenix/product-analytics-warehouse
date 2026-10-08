# GA4 sample deployment and validation

## Source and limits

Google's [public ecommerce sample](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset) contains obfuscated Google Merchandise Store exports from **2020-11-01 through 2021-01-31** in `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`. Google's documentation warns that fields may hold `<Other>`, `NULL`, or empty strings and that internal consistency is limited. The sample does not contain the newer batch identity fields ([Google query guide](https://developers.google.com/analytics/bigquery/basic-queries)). [`bigquery/ga4_profile.sql`](../bigquery/ga4_profile.sql) was executed in the US region on 2026-10-08; the observed nulls, mismatches, and job usage are in [`reports/ga4_profile.md`](../reports/ga4_profile.md).

The adapter keeps `view_item`, `add_to_cart`, `begin_checkout`, and `purchase` events. It derives UTC date from the event timestamp, user from `user_pseudo_id`, session from the `ga_session_id` event parameter, transaction ID and purchase revenue from `ecommerce`, and order items from `items`. User, session, revenue, currency, item IDs, price, and quantity may be absent. Missing values stay null. The raw event row hash plus an ordinal gives each identical source row a unique key for a stable *multiset*, but it cannot identify one physically identical event across source revisions.

Order revenue and item sums may differ because of missing values, discounts, tax, shipping, and sample obfuscation. The reconciliation test deliberately fails on differences greater than 0.01 when both sides are complete. Review its failure rows before choosing any business definition; do not rewrite one side to force agreement. Different currencies are not summed together.

## Current Sandbox deployment

The project `gen-lang-client-0195528254` remains in BigQuery Sandbox. Its existing Retailrocket views and ten `ga4_` views share the `product_analytics_warehouse` dataset. Generate the GA4 views from the dbt SELECT bodies, then run the resulting script in BigQuery Studio in the US region:

```bash
python3 -m warehouse.ga4_sandbox --project gen-lang-client-0195528254
```

The generated [`bigquery/ga4_sandbox_views.sql`](../bigquery/ga4_sandbox_views.sql) was deployed on 2026-10-08. Its script completed all ten `CREATE OR REPLACE VIEW` statements. [`reports/ga4_sandbox_validation.md`](../reports/ga4_sandbox_validation.md) records the executed key checks and monetary reconciliation. These views query the fixed historical public sample when read; they do not run an incremental refresh or write materialized tables.

## DML-capable deployment, if billing is enabled later

1. Create a billable BigQuery project with the BigQuery API enabled and a `product_analytics_dbt` dataset in the US region. The dbt incremental `merge` strategy requires BigQuery DML, which the current Sandbox does not support.
2. Install `dbt-bigquery` in a Python environment. Copy `profiles.yml.example` to `profiles.yml`, set the project ID, and authenticate with Google Cloud. Keep `profiles.yml` untracked.
3. Run `dbt debug --profiles-dir .`, then `dbt build --profiles-dir .` from the repository root. The default variables cover the complete public sample. To process or reprocess one source day, use `dbt build --profiles-dir . --vars '{"ga4_start_date":"20201101","ga4_end_date":"20201101"}'`. A full refresh rebuilds from the selected range, so pass the entire desired range with `--full-refresh`.
4. Run the profile SQL and record its result, then inspect dbt test failures. Execute the same daily build twice and compare row counts, distinct event IDs, orders, and total revenue by currency to check idempotence. Verify the item count against the selected purchase events' nested array lengths.

The staging table is partitioned on UTC `event_date`, clustered on event name and user ID, and merged on `event_id`. The marts are replaced on each build so corrections propagate throughout cohorts and orders. A daily backfill uses the date variables; rebuilding a revised source file with additional *identical* rows can change duplicate ordinals, so use `--full-refresh` for that case.

## Airflow

Install `apache-airflow-providers-google` and `dbt-bigquery` in the worker image. Mount this repository and the dbt profile at the path in `PAW_DBT_DIR`; set `PAW_PROJECT` and `PAW_DATASET` to the dbt target, then set `PAW_ALERT_EMAIL` and configure Airflow email delivery for failure alerts. Place [`product_analytics_ga4.py`](../airflow/dags/product_analytics_ga4.py) in the DAG folder. The DAG checks that the public daily table has rows, runs `dbt build` as the transformation and quality gate, then records the completion timestamp in `pipeline_refresh`. It is bounded to the historical sample and has `catchup=False`; use an explicit Airflow backfill for 2020-11-01 through 2021-01-31. The DAG has not been deployed or executed here.

## Dashboard and operating evidence

The existing [Retailrocket dashboard](../dashboard/retailrocket.html) and [findings](../reports/retailrocket_findings.md) are the completed real-data presentation. The [GA4 Data Studio report](https://datastudio.google.com/u/0/reporting/767fba24-ec08-454b-bfd8-5e4d37940f8d) connects to the Sandbox views and has three verified pages: daily users, session funnel, and week-one retention. Each page has a date control defaulting to 2020-11-02 through 2021-01-18. The retention chart displays the rate as a 0–1 fraction. Captures exported from the report are in [`reports/screenshots`](../reports/screenshots). The funnel model has one row per date of first item view in a session; sum its four stage columns for date-filtered cards. A session may reach later stages on subsequent dates. The dashboard has no Airflow refresh timestamp: views recompute when queried, while the Airflow `pipeline_refresh` table is for the future DML-capable deployment.

The [executed GA4 profile](../reports/ga4_profile.md) records its job ID, bytes processed and billed, slot milliseconds, and elapsed time. The [Sandbox view validation](../reports/ga4_sandbox_validation.md) lists its job IDs; [`bigquery/ga4_job_usage.sql`](../bigquery/ga4_job_usage.sql) was run for all six recorded jobs. Its [compact usage record](../reports/ga4_sandbox_job_usage.md) labels runtime and bytes as Sandbox quota usage, not monetary cost. For a reproducible full cost record after a DML-capable build, also collect the build jobs, regional query price, and table storage bytes. The local Retailrocket CSV contains 2,756,101 records (94,237,913 bytes); its SQLite database is an implementation artifact, not a BigQuery storage estimate.
