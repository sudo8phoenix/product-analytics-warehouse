# Build checklist

## Working local milestone

- [x] Define session funnel, DAU, weekly retention, UTC reporting, and channel attribution.
- [x] Document the grain and keys of each implemented table.
- [x] Ingest and validate event records; retain invalid rows and reasons.
- [x] Deduplicate events, upsert changed records, and handle late arrivals.
- [x] Build event, session, order, user, product, and date tables.
- [x] Query funnel, daily active users, cohort retention, and channel revenue.
- [x] Generate a local dashboard and three evidence-backed sample findings.
- [x] Test reruns for unchanged counts and revenue.

## Real-data and cloud milestone

- [ ] Get a Google Cloud project and BigQuery dataset; inspect the GA4 public ecommerce sample and document its date coverage and missing fields.
- [ ] Build a GA4-to-canonical-event extraction adapter, including nested item rows and transaction reconciliation.
- [ ] Add `fct_order_items` once item-level purchase data exists; validate order totals against items.
- [ ] Port transformations to dbt BigQuery incremental models with partitioning and clustering.
- [ ] Add dbt uniqueness, non-null, accepted-value, and relationship tests plus revenue reconciliation.
- [ ] Add an Airflow DAG for ingestion, transformations, quality gates, backfills, and failure alerts.
- [ ] Publish a Looker Studio dashboard with date filters and last successful refresh.
- [ ] Replace the sample report with three findings from real data, each with a limitation and next action.
- [ ] Measure real dataset volume, runtime, and BigQuery cost; add screenshots and a short demo.
