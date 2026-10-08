# GA4 public ecommerce sample profile

Executed in BigQuery Studio on 2026-10-08 against
`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`, with the
table suffix restricted to 2020-11-01 through 2021-01-31.
Project: `gen-lang-client-0195528254` (US, BigQuery Sandbox).
Query: [`bigquery/ga4_profile.sql`](../bigquery/ga4_profile.sql).
Job ID: `job_kLCgQGEvStNRkP8xawo-oJZF9CDy`.

| Measure | Result |
|---|---:|
| First / last source table | 20201101 / 20210131 |
| Events | 4,295,584 |
| Events missing user ID | 0 |
| Events missing GA4 session ID | 0 |
| Purchase events | 5,692 |
| Purchases missing transaction ID | 23 |
| Purchases missing purchase revenue | 450 |
| Purchases without items | 2 |
| Purchases with purchase revenue and item price × quantity differing by more than 0.01 | 1,328 |

The mismatch count is a diagnostic on purchase events, not a reconciled order
total. The sample is obfuscated and may contain inconsistent fields. Transaction
deduplication, currency, taxes, shipping, discounts, and missing values require
inspection before interpreting these differences as revenue errors.

The profile job processed 1,995,902,804 bytes, billed 1,996,488,704 bytes of
on-demand query usage, consumed 23,107 slot milliseconds, and ran for 4,918
milliseconds. These metrics came from
`region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT` for the job above.
The console displayed "Using on-demand processing quota" in the Sandbox;
these usage bytes are not a claim of an actual monetary charge.
