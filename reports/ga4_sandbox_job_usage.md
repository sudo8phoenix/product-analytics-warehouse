# GA4 Sandbox quota usage

On 2026-10-09, [`bigquery/ga4_job_usage.sql`](../bigquery/ga4_job_usage.sql) was run in the US region as job `job_T2PGqFAZVvb5bRXrLk0uiNZwGS5R`. It returned six recorded GA4 profile, view creation, and validation jobs. All six were `DONE` with no error. An aggregate query over the same six job IDs ran as `job_GpsbKyJeWGXOAtfRIDg0WxoYC2xj` and returned:

| Measure across six jobs | Observed value |
|---|---:|
| Bytes processed | 16,330,534,220 (15.21 GiB) |
| Bytes billed by on-demand accounting | 16,332,619,776 (15.21 GiB) |
| Sum of job elapsed time | 62,267 ms |
| Sum of slot time | 9,931,800 ms |

These are **Sandbox quota usage** figures, not a monetary cost or an elapsed wall-clock duration for a pipeline. The sum excludes newer exploratory queries, Looker Studio queries, storage, and any future dbt or Airflow jobs.
