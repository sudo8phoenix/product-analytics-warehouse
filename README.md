# Product Analytics Warehouse

A reproducible local warehouse for answering where shoppers leave the purchase funnel and which shoppers return. The checked-in dataset is **synthetic**; its numbers demonstrate the pipeline and must not be presented as real customer behavior.

## Quick start

Requires Python 3.10+; the local pipeline uses only the standard library.

```bash
python3 -m warehouse.cli run --input data/sample_events.jsonl --db build/warehouse.db
python3 -m warehouse.cli report --db build/warehouse.db --output reports/sample_findings.md
python3 -m warehouse.cli dashboard --db build/warehouse.db --output dashboard/index.html
python3 -m unittest discover -s tests -v
```

Open [`dashboard/index.html`](dashboard/index.html) in a browser. Run the `run` command twice: the second run should report zero inserted events and unchanged fact counts and revenue. The checked-in report and dashboard were generated from this fixture. `build/` is ignored by Git.

## Model and metric definitions

All event timestamps are UTC. An event is accepted only with a nonempty `event_id`, valid timestamp, and one of `view_item`, `add_to_cart`, `begin_checkout`, `purchase`. For duplicate `event_id`s, the record with the latest ingestion timestamp wins; equal timestamps are resolved by a stable payload sort. Changed versions are upserted. An anonymous event remains in `fct_events`, but is excluded from user and session metrics. A purchase without a transaction ID remains an event but is excluded from `fct_orders` and counted in quality warnings.

| Table | Grain | Key |
|---|---|---|
| `fct_events` | One deduplicated event | `event_id` |
| `fct_sessions` | One identifiable `(user_id, session_id)` with at least one event | `(user_id, session_id)` |
| `fct_orders` | One valid purchase transaction | `transaction_id` |
| `dim_users` | One identifiable user | `user_id` |
| `dim_products` | One referenced product | `product_id` |
| `dim_dates` | One UTC calendar date with an event | `date` |
| `rejected_records` | One invalid input record per source line and reason | `(source_hash, line_number)` |

`fct_events` is the source of event activity. `fct_orders` contains transaction revenue; never sum purchase event amounts and order revenue together. If more than one purchase event claims a transaction, the latest event timestamp wins, with `event_id` as a tie breaker. This dataset has one product per purchase event, so order items are not modeled.

The funnel is **session based** and ordered: view item → add to cart → begin checkout → valid order. A session reaches a stage only if it has reached the previous one earlier or at the same timestamp. Each session counts at most once per stage. DAU is distinct known users with any accepted event on a UTC date. Cohort week starts Monday and uses the user's first observed event; weekly retention is distinct users active in a later week divided by the original cohort size. Revenue uses the user's first observed nonempty acquisition channel, or `unknown`. Revenue is based on valid order transactions, not events. Observation windows should be complete before interpreting later cohort weeks.

## Project map

- [`warehouse/pipeline.py`](warehouse/pipeline.py): validation, deduplication, incremental upserts, dimensions, sessions, and orders.
- [`warehouse/analytics.py`](warehouse/analytics.py): funnel, DAU, weekly cohorts, and channel revenue queries.
- [`warehouse/cli.py`](warehouse/cli.py): pipeline, report, and self-contained dashboard commands.
- [`data/sample_events.jsonl`](data/sample_events.jsonl): synthetic fixture with duplicates, anonymous activity, and a late event.
- [`reports/sample_findings.md`](reports/sample_findings.md): three findings computed from the fixture.
- [`dashboard/index.html`](dashboard/index.html): static dashboard generated from the fixture.
- [`tests/test_pipeline.py`](tests/test_pipeline.py): idempotence, late-arrival, and data-quality checks.
- [`TODO.md`](TODO.md): remaining work and cloud deployment path.

## Limits and next step

The local source is synthetic and small. It does not estimate real conversion or retention. Google Analytics export has nested items, event parameters, consent effects, and attribution details that require a separate BigQuery adapter and validation before using real data. BigQuery, dbt, Airflow, and Looker Studio are planned in `TODO.md`; no cloud deployment is claimed.
