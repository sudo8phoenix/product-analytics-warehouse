"""Idempotent SQLite warehouse for canonical product events."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

EVENT_NAMES = {"view_item", "add_to_cart", "begin_checkout", "purchase"}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS fct_events (
  event_id TEXT PRIMARY KEY,
  event_ts TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  event_date TEXT NOT NULL,
  user_id TEXT,
  session_id TEXT,
  event_name TEXT NOT NULL,
  product_id TEXT,
  transaction_id TEXT,
  amount REAL,
  acquisition_channel TEXT,
  payload_sort TEXT NOT NULL,
  CHECK (event_name IN ('view_item','add_to_cart','begin_checkout','purchase'))
);
CREATE INDEX IF NOT EXISTS idx_events_date ON fct_events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_session ON fct_events(user_id, session_id, event_ts);
CREATE TABLE IF NOT EXISTS dim_users (
  user_id TEXT PRIMARY KEY,
  first_seen_at TEXT NOT NULL,
  acquisition_channel TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_products (product_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS dim_dates (date TEXT PRIMARY KEY, week_start TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fct_sessions (
  user_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT NOT NULL,
  PRIMARY KEY (user_id, session_id),
  FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
);
CREATE TABLE IF NOT EXISTS fct_orders (
  transaction_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  order_ts TEXT NOT NULL,
  order_date TEXT NOT NULL,
  user_id TEXT,
  amount REAL NOT NULL,
  FOREIGN KEY (event_id) REFERENCES fct_events(event_id),
  FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
);
CREATE TABLE IF NOT EXISTS rejected_records (
  source_hash TEXT NOT NULL,
  line_number INTEGER NOT NULL,
  reason TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (source_hash, line_number)
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def _timestamp(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp needs timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _optional(value: object) -> str | None:
    return str(value).strip() if value is not None and str(value).strip() else None


def _normalize(raw: dict) -> tuple:
    event_id = _optional(raw.get("event_id"))
    if not event_id:
        raise ValueError("missing event_id")
    event_name = raw.get("event_name")
    if event_name not in EVENT_NAMES:
        raise ValueError("invalid event_name")
    event_ts = _timestamp(raw.get("event_timestamp"))
    ingested_at = _timestamp(raw.get("ingested_at"))
    amount = raw.get("amount")
    if amount is not None:
        try:
            amount = float(amount)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid amount") from exc
        if not 0 <= amount < 1e12:
            raise ValueError("invalid amount")
    payload_sort = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    return (
        event_id, event_ts, ingested_at, event_ts[:10],
        _optional(raw.get("user_id")), _optional(raw.get("session_id")),
        event_name, _optional(raw.get("product_id")),
        _optional(raw.get("transaction_id")), amount,
        _optional(raw.get("acquisition_channel")), payload_sort,
    )


def _rebuild_derived(connection: sqlite3.Connection) -> None:
    """Recompute small derived tables from the deduplicated event source."""
    connection.execute("DELETE FROM fct_orders")
    connection.execute("DELETE FROM fct_sessions")
    connection.execute("DELETE FROM dim_users")
    connection.execute("DELETE FROM dim_products")
    connection.execute("DELETE FROM dim_dates")
    connection.execute("""
      INSERT INTO dim_users(user_id, first_seen_at, acquisition_channel)
      SELECT u.user_id, u.first_seen_at,
        COALESCE((SELECT e.acquisition_channel FROM fct_events e
                  WHERE e.user_id = u.user_id AND e.acquisition_channel IS NOT NULL
                  ORDER BY e.event_ts, e.event_id LIMIT 1), 'unknown')
      FROM (SELECT user_id, MIN(event_ts) AS first_seen_at FROM fct_events
            WHERE user_id IS NOT NULL GROUP BY user_id) u
    """)
    connection.execute("INSERT INTO dim_products SELECT DISTINCT product_id FROM fct_events WHERE product_id IS NOT NULL")
    connection.execute("""
      INSERT INTO dim_dates(date, week_start)
      SELECT DISTINCT event_date, date(event_date, '-' || ((CAST(strftime('%w', event_date) AS INTEGER) + 6) % 7) || ' days')
      FROM fct_events
    """)
    connection.execute("""
      INSERT INTO fct_sessions(user_id, session_id, started_at, ended_at)
      SELECT user_id, session_id, MIN(event_ts), MAX(event_ts)
      FROM fct_events WHERE user_id IS NOT NULL AND session_id IS NOT NULL
      GROUP BY user_id, session_id
    """)
    connection.execute("""
      INSERT INTO fct_orders(transaction_id, event_id, order_ts, order_date, user_id, amount)
      SELECT transaction_id, event_id, event_ts, event_date, user_id, amount
      FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY event_ts DESC, event_id DESC) AS rn
        FROM fct_events
        WHERE event_name = 'purchase' AND transaction_id IS NOT NULL AND amount IS NOT NULL
      ) WHERE rn = 1
    """)


def ingest(connection: sqlite3.Connection, input_path: str | Path) -> dict:
    content = Path(input_path).read_bytes()
    source_hash = hashlib.sha256(content).hexdigest()
    candidates: dict[str, tuple] = {}
    rejected = 0
    with connection:
        for line_number, line in enumerate(content.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("record must be an object")
                record = _normalize(raw)
                prior = candidates.get(record[0])
                if prior is None or (record[2], record[11]) > (prior[2], prior[11]):
                    candidates[record[0]] = record
            except (ValueError, json.JSONDecodeError) as exc:
                rejected += 1
                connection.execute(
                    "INSERT OR REPLACE INTO rejected_records VALUES (?, ?, ?, ?)",
                    (source_hash, line_number, str(exc), line),
                )
        inserted = updated = 0
        for record in candidates.values():
            prior = connection.execute(
                "SELECT ingested_at, payload_sort FROM fct_events WHERE event_id = ?", (record[0],)
            ).fetchone()
            if prior is not None and (record[2], record[11]) <= (prior[0], prior[1]):
                continue
            connection.execute("""
              INSERT INTO fct_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
              ON CONFLICT(event_id) DO UPDATE SET
                event_ts=excluded.event_ts, ingested_at=excluded.ingested_at,
                event_date=excluded.event_date, user_id=excluded.user_id,
                session_id=excluded.session_id, event_name=excluded.event_name,
                product_id=excluded.product_id, transaction_id=excluded.transaction_id,
                amount=excluded.amount, acquisition_channel=excluded.acquisition_channel,
                payload_sort=excluded.payload_sort
            """, record)
            if prior is None:
                inserted += 1
            else:
                updated += 1
        if inserted or updated:
            _rebuild_derived(connection)
    return {"inserted_events": inserted, "updated_events": updated, "rejected_input_lines": rejected}


def quality(connection: sqlite3.Connection) -> dict:
    queries = {
        "events": "SELECT COUNT(*) FROM fct_events",
        "sessions": "SELECT COUNT(*) FROM fct_sessions",
        "orders": "SELECT COUNT(*) FROM fct_orders",
        "revenue": "SELECT COALESCE(ROUND(SUM(amount), 2), 0) FROM fct_orders",
        "anonymous_events": "SELECT COUNT(*) FROM fct_events WHERE user_id IS NULL",
        "purchases_without_transaction": "SELECT COUNT(*) FROM fct_events WHERE event_name='purchase' AND transaction_id IS NULL",
        "purchases_without_amount": "SELECT COUNT(*) FROM fct_events WHERE event_name='purchase' AND amount IS NULL",
        "rejected_records": "SELECT COUNT(*) FROM rejected_records",
    }
    return {name: connection.execute(sql).fetchone()[0] for name, sql in queries.items()}
