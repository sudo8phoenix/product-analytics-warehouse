# BigQuery run

Target: `gen-lang-client-0195528254.product_analytics_warehouse` in the **US** multiregion. The source is the same Retailrocket `events.csv` used by the local run. Raw data is not committed; see the root README for the download and SHA-256.

## Load through the BigQuery console

1. In BigQuery Studio, open `product_analytics_warehouse` and select **Create table**.
2. Choose **Upload**, browse to `data/raw/events.csv`, choose **CSV**, and name the table `raw_events`.
3. Set **Header rows to skip** to `1` and enable **Auto detect**. The file is 94,237,913 bytes, under the [console's 100 MB local upload limit](https://docs.cloud.google.com/bigquery/docs/batch-loading-data#loading_data_from_local_files). The first successful load inferred the schema below; all five fields are nullable in the raw table.

| Field | BigQuery type | Nullable |
|---|---|---|
| `timestamp` | `INT64` | Yes |
| `visitorid` | `INT64` | Yes |
| `event` | `STRING` | Yes |
| `itemid` | `INT64` | Yes |
| `transactionid` | `INT64` | Yes |

Run [`retailrocket_views.sql`](retailrocket_views.sql) after replacing `PROJECT_ID` with the project ID. Then run [`verify.sql`](verify.sql) with the same replacement. For reruns, **replace** `raw_events` with the same file and rerun the view script. Appending the same file would double counts.

## Verified cloud results

The BigQuery console created `raw_events` from the full file and reported 2,756,101 rows (79.5 MB logical storage). All nine `CREATE OR REPLACE VIEW` statements completed successfully. Query results matched the local run:

| Check | BigQuery result |
|---|---:|
| Raw rows / event rows / distinct event IDs | 2,756,101 each |
| Distinct transaction orders | 17,672 |
| Distinct visitors | 1,407,580 |
| Ordered view → cart → purchase visitors | 1,404,179 → 32,934 → 9,952 |
| Week-one return, 2015-05-04 cohort | 3,425 / 71,389 = 4.8% |
| Peak daily active visitors | 17,516 on 2015-07-26 |

These figures are observed event counts, not revenue. BigQuery views compute their results from `raw_events`; their creation does not materialize copies of the data.

## Overwrite rerun check

The same `events.csv` was loaded a second time with **Write preference → Overwrite table** and **Header rows to skip → 1**. The second load succeeded. A fresh query after the overwrite returned the same 2,756,101 raw rows, 2,756,101 event rows, 2,756,101 distinct event IDs, 17,672 orders, and 1,407,580 visitors. The ordered funnel stayed at 1,404,179 → 32,934 → 9,952, and the 2015-05-04 cohort stayed at 3,425 / 71,389 = 4.8%. This verifies that a full source rerun does not double count records when the load uses overwrite. It does not establish incremental merge behavior; that remains future work.

The source has no event ID. The BigQuery `event_id` combines a hash of the source fields with an ordinal for identical rows. This preserves every source row and produces a stable multiset of IDs on repeat loads; it cannot recover the identity of identical source events. The source also lacks session IDs, checkout, prices, and acquisition channels.

BigQuery Sandbox supports this batch load and SQL views, but [does not support DML or streaming](https://docs.cloud.google.com/bigquery/docs/sandbox#limitations). Its tables and views expire after 60 days. The dataset and load must remain within the sandbox storage limit. No billing upgrade is needed for this run.
