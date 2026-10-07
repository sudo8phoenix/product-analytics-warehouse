# Findings from authentic Retailrocket events

Source: [Retailrocket ecommerce dataset](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset) (CC BY-NC-SA 4.0), `events.csv`, SHA-256 `3745aa83238b1e6d44d8fda209807899f420084398f94ddf745f3cbcfecbf9e7`. The source describes anonymized events from a real ecommerce site. This analysis uses all 2,756,101 source rows from 2015-05-03 to 2015-09-18 UTC.

1. **View → cart is the largest observed drop:** 1,404,179 visitors viewed an item, 32,934 subsequently added to cart, and 97.65% did not progress. Next action: examine product pages and item availability; this is an observed association, not a causal result.
2. **Week-1 return:** The complete-week cohort starting 2015-05-04 has 3,425 of 71,389 visitors active in the next calendar week (4.80%). Next action: compare later complete cohorts and investigate repeat-visit journeys.
3. **Peak daily activity:** 2015-07-26 had 17,516 active visitors, the most in this observation window. Next action: compare event mix and campaigns if external campaign data becomes available.

## Counts and definitions

| Measure | Result |
|---|---:|
| Event rows | 2,756,101 |
| Visitors | 1,407,580 |
| Views | 2,664,312 |
| Cart adds | 69,332 |
| Transaction item events | 22,457 |
| Distinct transaction IDs | 17,672 |
| Ordered view → cart → transaction visitors | 9,952 |

The funnel counts **visitors across the whole observed period**, with stages in timestamp order. It does not imply the same product or session. A source row is the event key because the file has no event ID. Multiple transaction item events can share one transaction ID; order counts deduplicate them. Week-1 return means activity in the next Monday–Sunday UTC week after the first observed week. The initial and final calendar weeks are partial. The source has no checkout, session ID, prices, revenue, or acquisition channel; none are estimated here. Source event timestamps were reused in the warehouse's `ingested_at` field because original ingestion timestamps are unavailable; that field must not be interpreted as ingestion latency.
