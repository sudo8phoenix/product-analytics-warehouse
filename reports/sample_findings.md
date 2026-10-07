# Sample findings — synthetic events

Generated from the current local warehouse. These are demonstration results, not claims about real customers.

1. **Largest funnel loss:** view_item → add_to_cart loses 37.5% of eligible sessions (8 → 5). Next action: inspect this transition with real event data and checkout diagnostics.
2. **Return behavior:** The 2026-09-28 cohort returned in week 1 at 40.0% (2 of 5 users). Next action: collect complete later observation weeks before comparing cohorts.
3. **Revenue channel:** `organic` leads this sample with 2 orders and 150.00 in source currency units. Next action: validate acquisition attribution and compare channel conversion on real data.

## Evidence and limits

- Accepted events: 23; sessions: 9; valid orders: 3; total revenue: 230.00.
- Anonymous events: 1; purchases without transaction ID: 1; rejected input records: 1.
- The sample is synthetic, small, and has intentionally incomplete later weeks. A session enters the funnel only when each preceding event occurs in order. Purchase revenue requires a transaction ID and amount.
