"""Render the dbt SELECT models as BigQuery Sandbox-compatible views.

This is a deployment alternative for environments without BigQuery DML.
The generated views use the same SQL bodies as the dbt models and are
prefixed with ga4_ to coexist with the Retailrocket views.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from jinja2 import Environment, StrictUndefined

MODEL_ORDER = (
    "staging/stg_ga4_events",
    "marts/fct_events",
    "marts/fct_orders",
    "marts/fct_order_items",
    "marts/dim_users",
    "marts/dim_products",
    "marts/dim_dates",
    "marts/metric_daily_active_users",
    "marts/metric_week1_retention",
    "marts/metric_session_funnel",
)
DEFAULT_VARS = {
    "ga4_start_date": "20201101",
    "ga4_end_date": "20210131",
    "ga4_source_project": "bigquery-public-data",
    "ga4_source_dataset": "ga4_obfuscated_sample_ecommerce",
}


def render_views(project: str, dataset: str, models_dir: Path) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9-]+", project) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", dataset):
        raise ValueError("project and dataset must be plain BigQuery identifiers")
    env = Environment(undefined=StrictUndefined)
    env.globals.update(
        config=lambda **kwargs: "",
        ref=lambda name: f"`{project}.{dataset}.ga4_{name}`",
        var=lambda name: DEFAULT_VARS[name],
    )
    statements = []
    for name in MODEL_ORDER:
        path = models_dir / f"{name}.sql"
        sql = env.from_string(path.read_text(encoding="utf-8")).render().strip().rstrip(";")
        target = f"`{project}.{dataset}.ga4_{name.rsplit('/', 1)[-1]}`"
        statements.append(f"CREATE OR REPLACE VIEW {target} AS\n{sql};")
    return "-- Generated from models/ by python -m warehouse.ga4_sandbox\n\n" + "\n\n".join(statements) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--dataset", default="product_analytics_warehouse")
    parser.add_argument("--output", type=Path, default=Path("bigquery/ga4_sandbox_views.sql"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sql = render_views(args.project, args.dataset, root / "models")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(sql, encoding="utf-8")
    print(f"Wrote {len(MODEL_ORDER)} views to {args.output}")


if __name__ == "__main__":
    main()
