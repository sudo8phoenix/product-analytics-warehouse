{{ config(unique_key='event_id', on_schema_change='sync_all_columns') }}

WITH source AS (
  SELECT t.*,
    TO_HEX(SHA256(TO_JSON_STRING(t))) AS source_hash,
    ROW_NUMBER() OVER (
      PARTITION BY TO_JSON_STRING(t) ORDER BY event_timestamp
    ) AS duplicate_ordinal
  FROM `{{ var('ga4_source_project') }}.{{ var('ga4_source_dataset') }}.events_*` t
  WHERE _TABLE_SUFFIX BETWEEN '{{ var('ga4_start_date') }}' AND '{{ var('ga4_end_date') }}'
), canonical AS (
  SELECT
    CONCAT('ga4:', source_hash, ':', CAST(duplicate_ordinal AS STRING)) AS event_id,
    TIMESTAMP_MICROS(event_timestamp) AS event_ts,
    DATE(TIMESTAMP_MICROS(event_timestamp)) AS event_date,
    NULLIF(user_pseudo_id, '') AS user_id,
    CAST((SELECT value.int_value FROM UNNEST(event_params)
      WHERE key = 'ga_session_id' LIMIT 1) AS STRING) AS session_id,
    event_name,
    NULLIF(ecommerce.transaction_id, '') AS transaction_id,
    SAFE_CAST(ecommerce.purchase_revenue AS NUMERIC) AS purchase_revenue,
    (SELECT COALESCE(value.double_value, CAST(value.int_value AS FLOAT64),
      SAFE_CAST(value.string_value AS FLOAT64)) FROM UNNEST(event_params)
      WHERE key = 'value' LIMIT 1) AS event_value,
    (SELECT value.string_value FROM UNNEST(event_params)
      WHERE key = 'currency' LIMIT 1) AS currency,
    NULLIF(traffic_source.source, '') AS acquisition_channel,
    items
  FROM source
)
SELECT * FROM canonical
WHERE event_name IN ('view_item', 'add_to_cart', 'begin_checkout', 'purchase')
