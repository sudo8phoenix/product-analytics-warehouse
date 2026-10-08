SELECT event_id, event_ts, event_date, user_id, session_id, event_name,
  transaction_id, purchase_revenue, event_value, currency, acquisition_channel
FROM {{ ref('stg_ga4_events') }}
