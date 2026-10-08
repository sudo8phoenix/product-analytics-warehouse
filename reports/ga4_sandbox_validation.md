# GA4 Sandbox view deployment

On 2026-10-08, the ten views in
[`bigquery/ga4_sandbox_views.sql`](../bigquery/ga4_sandbox_views.sql)
were created in `gen-lang-client-0195528254.product_analytics_warehouse`
(US). BigQuery script job `job_M8IUMOjc_tV-0TLub-TuBXSxJrfu`
reported **10 statements processed, all successful**. The views use the
`ga4_` prefix and leave the Retailrocket views intact.
The checks below can be repeated with
[`bigquery/ga4_sandbox_validate.sql`](../bigquery/ga4_sandbox_validate.sql).

| Executed check | Result | Job ID |
|---|---:|---|
| Canonical ecommerce events / distinct event IDs | 489,060 / 489,060 | `job_B3-NOzb7OlWnrl7_CbpTNElFUfaE` |
| Purchase events / with transaction ID | 5,692 / 5,669 | same |
| Deduplicated orders / order items | 4,452 / 13,233 | `job_pf_cnsrX7BKV2GoS1dWTJwXR1c2I` |
| Users / UTC dates / DAU dates | 61,335 / 92 / 92 | same |
| Cohort weeks / sessions with an item view | 14 / 77,020 | same |
| Duplicate event / order / order-item keys | 0 / 0 / 0 | `job_BZx3M1hZTCz4ri3R8XWt4jDwnhGF` |
| Order items without an order | 0 | same |

The monetary reconciliation job `job_NPRe_0YyrYCB3lMiiMZuvLbebjvt`
found 3,333 orders whose purchase revenue matches the sum of item price ×
quantity within 0.01, 1,118 mismatches, and one order without purchase
revenue. Every modeled order has at least one item. The obfuscated sample
may contain internally inconsistent values; the differences remain visible
quality findings. No revenue total is presented as validated.

View creation processed zero source bytes. The validation queries read the
public sample under Sandbox on-demand quota. The views are subject to the
Sandbox expiration policy and recompute from the public sample when read.
