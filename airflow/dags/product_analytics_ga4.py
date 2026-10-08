"""GA4 public sample orchestration; requires Airflow Google provider and dbt-bigquery."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator

DBT_DIR = os.environ.get("PAW_DBT_DIR", "/opt/airflow/product-analytics-warehouse")
ALERT_EMAIL = os.environ.get("PAW_ALERT_EMAIL")
PROJECT = os.environ.get("PAW_PROJECT", "YOUR_PROJECT_ID")
DATASET = os.environ.get("PAW_DATASET", "product_analytics_dbt")

with DAG(
    dag_id="product_analytics_ga4",
    start_date=datetime(2020, 11, 1, tzinfo=timezone.utc),
    end_date=datetime(2021, 2, 1, tzinfo=timezone.utc),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=10),
        "email": [ALERT_EMAIL] if ALERT_EMAIL else [],
        "email_on_failure": bool(ALERT_EMAIL),
    },
    tags=["ga4", "analytics"],
) as dag:
    source_ready = BigQueryInsertJobOperator(
        task_id="source_ready",
        location="US",
        configuration={"query": {
            "query": """
              ASSERT (
                SELECT COUNT(*) > 0
                FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_{{ ds_nodash }}`
              ) AS 'GA4 source day is absent or empty';
            """,
            "useLegacySql": False,
        }},
    )
    transform_and_test = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {DBT_DIR} && dbt build --profiles-dir . "
            "--vars '{\"ga4_start_date\": \"{{ ds_nodash }}\", "
            "\"ga4_end_date\": \"{{ ds_nodash }}\"}'"
        ),
    )
    record_refresh = BigQueryInsertJobOperator(
        task_id="record_successful_refresh",
        location="US",
        configuration={"query": {
            "query": (
                f"CREATE OR REPLACE TABLE `{PROJECT}.{DATASET}.pipeline_refresh` AS "
                "SELECT CURRENT_TIMESTAMP() AS last_successful_refresh"
            ),
            "useLegacySql": False,
        }},
    )
    source_ready >> transform_and_test >> record_refresh
