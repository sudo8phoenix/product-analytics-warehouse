"""Queries over deduplicated facts; all dates and weeks are UTC."""

from __future__ import annotations

import sqlite3


def funnel(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute("""
      WITH views AS (
        SELECT s.user_id, s.session_id,
          (SELECT MIN(event_ts) FROM fct_events e WHERE e.user_id=s.user_id AND e.session_id=s.session_id AND event_name='view_item') AS viewed
        FROM fct_sessions s
      ), carts AS (
        SELECT v.*,
          (SELECT MIN(event_ts) FROM fct_events e WHERE e.user_id=v.user_id AND e.session_id=v.session_id AND event_name='add_to_cart' AND e.event_ts>=v.viewed) AS carted
        FROM views v
      ), checkouts AS (
        SELECT c.*,
          (SELECT MIN(event_ts) FROM fct_events e WHERE e.user_id=c.user_id AND e.session_id=c.session_id AND event_name='begin_checkout' AND e.event_ts>=c.carted) AS checkout
        FROM carts c
      ), stages AS (
        SELECT c.*,
          (SELECT MIN(e.event_ts) FROM fct_orders o JOIN fct_events e ON e.event_id=o.event_id
           WHERE e.user_id=c.user_id AND e.session_id=c.session_id AND e.event_ts>=c.checkout) AS purchased
        FROM checkouts c
      )
      SELECT
        SUM(viewed IS NOT NULL) AS viewed,
        SUM(viewed IS NOT NULL AND carted >= viewed) AS carted,
        SUM(viewed IS NOT NULL AND carted >= viewed AND checkout >= carted) AS checkout,
        SUM(viewed IS NOT NULL AND carted >= viewed AND checkout >= carted AND purchased >= checkout) AS purchased
      FROM stages
    """).fetchone()
    names = ["view_item", "add_to_cart", "begin_checkout", "purchase"]
    counts = [int(value or 0) for value in rows]
    return [
        {"stage": name, "sessions": count,
         "dropoff_from_previous_pct": None if i == 0 or counts[i - 1] == 0 else round(100 * (1 - count / counts[i - 1]), 1)}
        for i, (name, count) in enumerate(zip(names, counts))
    ]


def daily_active_users(connection: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in connection.execute("""
      SELECT event_date AS date, COUNT(DISTINCT user_id) AS active_users
      FROM fct_events WHERE user_id IS NOT NULL
      GROUP BY event_date ORDER BY event_date
    """)]


def cohort_retention(connection: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in connection.execute("""
      WITH cohorts AS (
        SELECT user_id, date(substr(first_seen_at,1,10),
          '-' || ((CAST(strftime('%w', substr(first_seen_at,1,10)) AS INTEGER)+6)%7) || ' days') AS cohort_week
        FROM dim_users
      ), activity AS (
        SELECT DISTINCT user_id,
          date(event_date, '-' || ((CAST(strftime('%w', event_date) AS INTEGER)+6)%7) || ' days') AS active_week
        FROM fct_events WHERE user_id IS NOT NULL
      ), sizes AS (
        SELECT cohort_week, COUNT(*) AS cohort_users FROM cohorts GROUP BY cohort_week
      )
      SELECT c.cohort_week,
        CAST((julianday(a.active_week)-julianday(c.cohort_week))/7 AS INTEGER) AS week_number,
        s.cohort_users, COUNT(DISTINCT c.user_id) AS retained_users,
        ROUND(100.0*COUNT(DISTINCT c.user_id)/s.cohort_users, 1) AS retention_pct
      FROM cohorts c JOIN activity a ON a.user_id=c.user_id AND a.active_week>=c.cohort_week
      JOIN sizes s ON s.cohort_week=c.cohort_week
      GROUP BY c.cohort_week, week_number ORDER BY c.cohort_week, week_number
    """)]


def channel_revenue(connection: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in connection.execute("""
      SELECT COALESCE(u.acquisition_channel, 'unknown') AS channel,
        COUNT(o.transaction_id) AS orders, ROUND(COALESCE(SUM(o.amount),0),2) AS revenue
      FROM fct_orders o LEFT JOIN dim_users u ON o.user_id=u.user_id
      GROUP BY channel ORDER BY revenue DESC, channel
    """)]
