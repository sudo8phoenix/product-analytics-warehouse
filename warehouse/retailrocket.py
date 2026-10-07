"""Load and analyze the authentic Retailrocket public event log.

The source has no event IDs, session IDs, prices, checkout, or channel. Source
line number is therefore the stable event key for a *specific* source file.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .pipeline import connect

SOURCE_URL = "https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset"
EVENT_MAP = {"view": "view_item", "addtocart": "add_to_cart", "transaction": "purchase"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _record(row: dict, line_number: int) -> tuple:
    if row["event"] not in EVENT_MAP:
        raise ValueError(f"unexpected event on line {line_number}")
    timestamp = datetime.fromtimestamp(int(row["timestamp"]) / 1000, tz=timezone.utc)
    event_ts = timestamp.isoformat(timespec="microseconds")
    user_id = row["visitorid"].strip()
    if not user_id:
        raise ValueError(f"missing visitor on line {line_number}")
    transaction_id = row["transactionid"].strip() or None
    return (
        f"rr:{line_number}", event_ts, event_ts, event_ts[:10], user_id, None,
        EVENT_MAP[row["event"]], row["itemid"].strip() or None,
        transaction_id, None, None, str(line_number),
    )


def load_csv(csv_path: Path, db_path: Path) -> dict:
    csv_path = Path(csv_path)
    source_hash = sha256_file(csv_path)
    connection = connect(db_path)
    connection.execute("""
      CREATE TABLE IF NOT EXISTS source_manifest (
        source_name TEXT PRIMARY KEY, sha256 TEXT NOT NULL, source_rows INTEGER NOT NULL
      )
    """)
    old = connection.execute("SELECT sha256, source_rows FROM source_manifest WHERE source_name='retailrocket'").fetchone()
    if old and old[0] != source_hash:
        raise ValueError("database contains a different Retailrocket CSV; use a fresh database")
    if not old and connection.execute("SELECT EXISTS(SELECT 1 FROM fct_events LIMIT 1)").fetchone()[0]:
        raise ValueError("database already contains events from another source; use a fresh database")
    if old:
        counts = profile(connection)
        connection.close()
        return {"inserted_events": 0, "source_rows": old[1], **counts}

    count = 0
    batch = []
    with csv_path.open(newline="", encoding="utf-8") as stream, connection:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["timestamp", "visitorid", "event", "itemid", "transactionid"]:
            raise ValueError(f"unexpected columns: {reader.fieldnames}")
        for line_number, row in enumerate(reader, start=2):
            batch.append(_record(row, line_number))
            count += 1
            if len(batch) == 10000:
                connection.executemany("INSERT INTO fct_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", batch)
                batch.clear()
        if batch:
            connection.executemany("INSERT INTO fct_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        connection.execute("""
          INSERT INTO dim_users(user_id,first_seen_at,acquisition_channel)
          SELECT user_id,MIN(event_ts),'unknown' FROM fct_events GROUP BY user_id
        """)
        connection.execute("INSERT INTO dim_products SELECT DISTINCT product_id FROM fct_events WHERE product_id IS NOT NULL")
        connection.execute("""
          INSERT INTO dim_dates(date,week_start)
          SELECT DISTINCT event_date, date(event_date,
            '-' || ((CAST(strftime('%w',event_date) AS INTEGER)+6)%7) || ' days')
          FROM fct_events
        """)
        connection.execute("""
          INSERT INTO fct_orders(transaction_id,event_id,order_ts,order_date,user_id,amount)
          SELECT transaction_id,event_id,event_ts,event_date,user_id,NULL
          FROM (
            SELECT *, ROW_NUMBER() OVER (
              PARTITION BY transaction_id ORDER BY event_ts DESC,event_id DESC
            ) AS rn
            FROM fct_events WHERE event_name='purchase' AND transaction_id IS NOT NULL
          ) WHERE rn=1
        """)
        connection.execute("INSERT INTO source_manifest VALUES ('retailrocket',?,?)", (source_hash, count))
    result = {"inserted_events": count, "source_rows": count, **profile(connection)}
    connection.close()
    return result


def profile(connection: sqlite3.Connection) -> dict:
    row = connection.execute("""
      SELECT COUNT(*) AS events,COUNT(DISTINCT user_id) AS visitors,
        MIN(event_date) AS first_date,MAX(event_date) AS last_date,
        SUM(event_name='view_item') AS views,
        SUM(event_name='add_to_cart') AS cart_adds,
        SUM(event_name='purchase') AS transaction_events
      FROM fct_events
    """).fetchone()
    result = dict(row)
    result["orders"] = connection.execute("SELECT COUNT(*) FROM fct_orders").fetchone()[0]
    return result


def visitor_funnel(connection: sqlite3.Connection) -> list[dict]:
    row = connection.execute("""
      WITH views AS (
        SELECT user_id,MIN(event_ts) AS viewed FROM fct_events
        WHERE event_name='view_item' GROUP BY user_id
      ), carts AS (
        SELECT e.user_id,MIN(e.event_ts) AS carted FROM fct_events e
        JOIN views v ON v.user_id=e.user_id AND e.event_ts>=v.viewed
        WHERE e.event_name='add_to_cart' GROUP BY e.user_id
      ), purchases AS (
        SELECT e.user_id,MIN(e.event_ts) AS purchased
        FROM fct_orders o JOIN fct_events e ON e.event_id=o.event_id
        JOIN carts c ON c.user_id=e.user_id AND e.event_ts>=c.carted
        GROUP BY e.user_id
      )
      SELECT (SELECT COUNT(*) FROM views),(SELECT COUNT(*) FROM carts),
        (SELECT COUNT(*) FROM purchases)
    """).fetchone()
    counts = list(row)
    return [
        {"stage": name, "visitors": count,
         "dropoff_from_previous_pct": None if i == 0 else round(100 * (1 - count / counts[i - 1]), 2)}
        for i, (name, count) in enumerate(zip(("view_item", "add_to_cart", "purchase"), counts))
    ]


def weekly_return(connection: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in connection.execute("""
      WITH cohorts AS (
        SELECT user_id,date(substr(first_seen_at,1,10),
          '-' || ((CAST(strftime('%w',substr(first_seen_at,1,10)) AS INTEGER)+6)%7) || ' days') AS cohort_week
        FROM dim_users
      ), activity AS (
        SELECT DISTINCT user_id,date(event_date,
          '-' || ((CAST(strftime('%w',event_date) AS INTEGER)+6)%7) || ' days') AS active_week
        FROM fct_events
      ), sizes AS (
        SELECT cohort_week,COUNT(*) AS cohort_users FROM cohorts GROUP BY cohort_week
      )
      SELECT c.cohort_week,s.cohort_users,COUNT(DISTINCT a.user_id) AS returned_users,
        ROUND(100.0*COUNT(DISTINCT a.user_id)/s.cohort_users,2) AS week_1_return_pct
      FROM cohorts c LEFT JOIN activity a ON a.user_id=c.user_id
        AND a.active_week=date(c.cohort_week,'+7 days')
      JOIN sizes s ON s.cohort_week=c.cohort_week
      GROUP BY c.cohort_week ORDER BY c.cohort_week
    """)]


def daily_active(connection: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in connection.execute("""
      SELECT event_date AS date,COUNT(DISTINCT user_id) AS active_visitors
      FROM fct_events GROUP BY event_date ORDER BY event_date
    """)]


def _table(rows: list[dict]) -> str:
    if not rows:
        return "<p>No data</p>"
    cols = list(rows[0])
    return "<table><thead><tr>" + "".join(f"<th>{html.escape(col.replace('_',' ').title())}</th>" for col in cols) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{html.escape(str(row[col])) if row[col] is not None else '—'}</td>" for col in cols) + "</tr>" for row in rows) + "</tbody></table>"


def publish(db_path: Path, report_path: Path, dashboard_path: Path) -> dict:
    connection = connect(db_path)
    p = profile(connection)
    funnel = visitor_funnel(connection)
    returns = weekly_return(connection)
    dau = daily_active(connection)
    source_hash = connection.execute("SELECT sha256 FROM source_manifest WHERE source_name='retailrocket'").fetchone()[0]
    connection.close()
    first_date = date.fromisoformat(p["first_date"])
    last_date = date.fromisoformat(p["last_date"])
    complete_week_1 = [
        r for r in returns
        if (cohort_start := date.fromisoformat(r["cohort_week"])) >= first_date
        and cohort_start + timedelta(days=13) <= last_date
    ]
    cohort = complete_week_1[0] if complete_week_1 else None
    peak = max(dau, key=lambda r: r["active_visitors"])
    report = f"""# Findings from authentic Retailrocket events

Source: [Retailrocket ecommerce dataset]({SOURCE_URL}) (CC BY-NC-SA 4.0), `events.csv`, SHA-256 `{source_hash}`. The source describes anonymized events from a real ecommerce site. This analysis uses all {p['events']:,} source rows from {p['first_date']} to {p['last_date']} UTC.

1. **View → cart is the largest observed drop:** {funnel[0]['visitors']:,} visitors viewed an item, {funnel[1]['visitors']:,} subsequently added to cart, and {funnel[1]['dropoff_from_previous_pct']:.2f}% did not progress. Next action: examine product pages and item availability; this is an observed association, not a causal result.
2. **Week-1 return:** The complete-week cohort starting {cohort['cohort_week']} has {cohort['returned_users']:,} of {cohort['cohort_users']:,} visitors active in the next calendar week ({cohort['week_1_return_pct']:.2f}%). Next action: compare later complete cohorts and investigate repeat-visit journeys.
3. **Peak daily activity:** {peak['date']} had {peak['active_visitors']:,} active visitors, the most in this observation window. Next action: compare event mix and campaigns if external campaign data becomes available.

## Counts and definitions

| Measure | Result |
|---|---:|
| Event rows | {p['events']:,} |
| Visitors | {p['visitors']:,} |
| Views | {p['views']:,} |
| Cart adds | {p['cart_adds']:,} |
| Transaction item events | {p['transaction_events']:,} |
| Distinct transaction IDs | {p['orders']:,} |
| Ordered view → cart → transaction visitors | {funnel[2]['visitors']:,} |

The funnel counts **visitors across the whole observed period**, with stages in timestamp order. It does not imply the same product or session. A source row is the event key because the file has no event ID. Multiple transaction item events can share one transaction ID; order counts deduplicate them. Week-1 return means activity in the next Monday–Sunday UTC week after the first observed week. The initial and final calendar weeks are partial. The source has no checkout, session ID, prices, revenue, or acquisition channel; none are estimated here. Source event timestamps were reused in the warehouse's `ingested_at` field because original ingestion timestamps are unavailable; that field must not be interpreted as ingestion latency.
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    cards = "".join(f"<div class='card'><span>{label}</span><strong>{value:,}</strong></div>" for label,value in [("Events",p["events"]),("Visitors",p["visitors"]),("Orders",p["orders"])])
    sections = "".join(f"<section><h2>{title}</h2>{_table(rows)}</section>" for title,rows in [("Ordered visitor funnel",funnel),("Weekly return by first-seen cohort",returns),("Daily active visitors",dau)])
    dashboard = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retailrocket warehouse</title><style>
    :root{{font-family:system-ui,sans-serif;background:#f4f6f8;color:#1d2935}}body{{max-width:1100px;margin:auto;padding:32px 20px 64px}}.note{{color:#526473;line-height:1.5}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:28px 0}}.card,section{{background:white;border:1px solid #dbe3e9;border-radius:12px;padding:20px}}.card span{{display:block;color:#526473;font-size:.85rem}}.card strong{{font-size:1.8rem}}section{{margin-top:16px;overflow-x:auto}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:10px 8px;border-bottom:1px solid #e7edf1}}th{{color:#526473;font-size:.78rem;text-transform:uppercase}}tr:last-child td{{border:0}}
    </style></head><body><h1>Retailrocket product behavior</h1><p class="note">Authentic anonymized event log · {p['first_date']} to {p['last_date']} UTC · Visitor-level funnel</p><div class="cards">{cards}</div>{sections}<p class="note">No checkout, revenue, acquisition channel, or native session ID in the source. See the report for definitions and limitations.</p></body></html>"""
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(dashboard, encoding="utf-8")
    return {"profile":p,"funnel":funnel,"cohort_example":cohort,"peak_day":peak,"source_sha256":source_hash}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    load = sub.add_parser("load")
    load.add_argument("--csv", required=True, type=Path)
    load.add_argument("--db", default="build/retailrocket.db", type=Path)
    report = sub.add_parser("publish")
    report.add_argument("--db", default="build/retailrocket.db", type=Path)
    report.add_argument("--report", default="reports/retailrocket_findings.md", type=Path)
    report.add_argument("--dashboard", default="dashboard/retailrocket.html", type=Path)
    args = parser.parse_args()
    result = load_csv(args.csv, args.db) if args.command == "load" else publish(args.db, args.report, args.dashboard)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
