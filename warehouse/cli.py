"""Run pipeline and publish a sample report/dashboard."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from .analytics import channel_revenue, cohort_retention, daily_active_users, funnel
from .pipeline import connect, ingest, quality


def _results(connection):
    return {
        "quality": quality(connection),
        "funnel": funnel(connection),
        "daily_active_users": daily_active_users(connection),
        "cohort_retention": cohort_retention(connection),
        "channel_revenue": channel_revenue(connection),
    }


def _report(data: dict) -> str:
    stages = data["funnel"]
    drop = max(stages[1:], key=lambda row: row["dropoff_from_previous_pct"] or -1)
    prev = stages[stages.index(drop) - 1]
    channels = data["channel_revenue"]
    top = channels[0] if channels else {"channel": "none", "revenue": 0, "orders": 0}
    cohorts = [r for r in data["cohort_retention"] if r["week_number"] == 1]
    retention = cohorts[0] if cohorts else None
    if retention:
        finding_2 = (f"The {retention['cohort_week']} cohort returned in week 1 at "
                     f"{retention['retention_pct']}% ({retention['retained_users']} of "
                     f"{retention['cohort_users']} users).")
    else:
        finding_2 = "The sample has no observed week-1 cohort activity; retention cannot be estimated."
    return f"""# Sample findings — synthetic events

Generated from the current local warehouse. These are demonstration results, not claims about real customers.

1. **Largest funnel loss:** {prev['stage']} → {drop['stage']} loses {drop['dropoff_from_previous_pct']}% of eligible sessions ({prev['sessions']} → {drop['sessions']}). Next action: inspect this transition with real event data and checkout diagnostics.
2. **Return behavior:** {finding_2} Next action: collect complete later observation weeks before comparing cohorts.
3. **Revenue channel:** `{top['channel']}` leads this sample with {top['orders']} orders and {top['revenue']:.2f} in source currency units. Next action: validate acquisition attribution and compare channel conversion on real data.

## Evidence and limits

- Accepted events: {data['quality']['events']}; sessions: {data['quality']['sessions']}; valid orders: {data['quality']['orders']}; total revenue: {data['quality']['revenue']:.2f}.
- Anonymous events: {data['quality']['anonymous_events']}; purchases without transaction ID: {data['quality']['purchases_without_transaction']}; rejected input records: {data['quality']['rejected_records']}.
- The sample is synthetic, small, and has intentionally incomplete later weeks. A session enters the funnel only when each preceding event occurs in order. Purchase revenue requires a transaction ID and amount.
"""


def _table(rows: list[dict]) -> str:
    if not rows:
        return "<p>No records.</p>"
    columns = list(rows[0])
    head = "".join(f"<th>{html.escape(key.replace('_', ' ').title())}</th>" for key in columns)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(row[key])) if row[key] is not None else '—'}</td>" for key in columns) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _dashboard(data: dict) -> str:
    q = data["quality"]
    cards = "".join(f"<div class='card'><span>{label}</span><strong>{value}</strong></div>" for label, value in [
        ("Events", q["events"]), ("Sessions", q["sessions"]),
        ("Orders", q["orders"]), ("Revenue", f"{q['revenue']:.2f}"),
    ])
    sections = "".join(f"<section><h2>{title}</h2>{_table(data[key])}</section>" for title, key in [
        ("Ordered session funnel", "funnel"), ("Daily active users", "daily_active_users"),
        ("Weekly cohort retention", "cohort_retention"), ("Revenue by acquisition channel", "channel_revenue"),
    ])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Product Analytics Warehouse</title><style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; background:#f4f6f8; color:#1d2935 }}
    body {{ max-width:1100px; margin:0 auto; padding:32px 20px 64px }} h1 {{ margin-bottom:4px }} .note {{ color:#526473; line-height:1.5 }}
    .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:28px 0 }} .card,section {{ background:white; border:1px solid #dbe3e9; border-radius:12px; padding:20px }} .card span {{ display:block; color:#526473; font-size:.85rem }} .card strong {{ display:block; font-size:1.8rem; margin-top:8px }}
    section {{ margin-top:16px; overflow-x:auto }} h2 {{ font-size:1.1rem; margin-top:0 }} table {{ width:100%; border-collapse:collapse }} th,td {{ text-align:left; padding:10px 8px; border-bottom:1px solid #e7edf1 }} th {{ color:#526473; font-size:.78rem; text-transform:uppercase; letter-spacing:.04em }} tr:last-child td {{ border:0 }}
    </style></head><body><h1>Product Analytics Warehouse</h1><p class="note">Synthetic sample · UTC dates · Session based funnel · Revenue in source currency units</p><div class="cards">{cards}</div>{sections}<p class="note">Generated from deduplicated warehouse facts. See README for metric definitions and limitations.</p></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--input", required=True)
    run.add_argument("--db", default="build/warehouse.db")
    for name in ("report", "dashboard"):
        command = sub.add_parser(name)
        command.add_argument("--db", default="build/warehouse.db")
        command.add_argument("--output", required=True)
    args = parser.parse_args()
    connection = connect(args.db)
    if args.command == "run":
        result = ingest(connection, args.input)
        print(json.dumps({**result, **quality(connection)}, indent=2))
    else:
        data = _results(connection)
        content = _report(data) if args.command == "report" else _dashboard(data)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
