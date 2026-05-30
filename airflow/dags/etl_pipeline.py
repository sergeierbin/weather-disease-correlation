"""
ETL pipeline DAG — orchestrates the full data flow:

    fetch_synthea ──┐
                    ├──> fetch_weather ──┐
    fetch_icd_codes ┘                   ├──> dbt_run
                    ────────────────────┘

Steps:
  1. fetch_synthea   — parse FHIR JSON bundles → raw.patients / encounters / organizations / conditions / organization_locations
  2. fetch_icd_codes — load icd_snomed.csv       → raw.icd10_codes         (runs in parallel with step 1)
  3. fetch_weather   — fetch weather (Meteostat) using coordinates from raw.organization_locations → raw.weather
  4. dbt_run         — run all dbt models       → staging / intermediate / marts
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# ── Failure callback ─────────────────────────────────────────────────────────

def on_failure(context):
    """Logs a prominent message on task failure. Airflow also sends email if SMTP is configured."""
    ti = context["task_instance"]
    log = context["task"].log
    log.error(
        "TASK FAILED — dag: %s  task: %s  run: %s",
        ti.dag_id, ti.task_id, ti.run_id,
    )

# ── Default task settings ────────────────────────────────────────────────────

_alert_email = os.environ.get("AIRFLOW_SMTP_MAIL_FROM") or None

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": on_failure,
    "email_on_failure": bool(_alert_email),
    "email": [_alert_email] if _alert_email else [],
}

# ── DAG definition ───────────────────────────────────────────────────────────

with DAG(
    dag_id="etl_pipeline",
    description="Synthea FHIR + ICD-10 + Meteostat weather → dbt star schema",
    # Trigger manually only — Synthea data is static and does not update automatically
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    # Do not backfill historical runs when the DAG is first activated
    catchup=False,
    default_args=default_args,
    tags=["etl"],
) as dag:

    # ── Step 1: ingest Synthea FHIR bundles ──────────────────────────────────
    # Reads every *.json file from /opt/airflow/synthea_output/fhir/
    # and upserts patients, encounters, and conditions into the raw schema.
    # ON CONFLICT DO NOTHING — safe to re-run on the same files.
    ingest_synthea = BashOperator(
        task_id="ingest_synthea",
        bash_command="python /opt/airflow/ingestion/fetch_synthea.py",
        execution_timeout=timedelta(hours=1),
    )

    # ── Step 2: ingest ICD-10 / SNOMED mapping ───────────────────────────────
    # Loads ingestion/icd_snomed.csv into raw.icd10_codes.
    # Runs in parallel with ingest_synthea — no shared state.
    ingest_icd_codes = BashOperator(
        task_id="ingest_icd_codes",
        bash_command="python /opt/airflow/ingestion/fetch_icd_codes.py",
        execution_timeout=timedelta(minutes=10),
    )

    # ── Step 3: ingest weather ───────────────────────────────────────────────
    # Fetches daily historical weather (Meteostat) → raw.weather.
    # Coordinates come from raw.organization_locations, populated by ingest_synthea.
    # Must run after ingest_synthea so organisation locations are available.
    ingest_weather = BashOperator(
        task_id="ingest_weather",
        bash_command="python /opt/airflow/ingestion/fetch_weather.py",
        execution_timeout=timedelta(hours=2),
    )

    # ── Step 4: run all dbt models ───────────────────────────────────────────
    # Executes the full dbt lineage:
    #   raw → staging (views) → intermediate (views) → marts (tables)
    # Must run after all ingestion tasks so the raw schema is fully populated.
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "/home/airflow/.local/bin/dbt run "
            "--project-dir /opt/airflow/dbt "
            "--profiles-dir /opt/airflow/dbt "
            "--log-path /tmp/dbt_logs "
            "--target-path /tmp/dbt_target"
        ),
        execution_timeout=timedelta(minutes=30),
    )

    # ── Task dependencies ─────────────────────────────────────────────────────
    # synthea must finish before weather (weather needs encounter + org data)
    ingest_synthea >> ingest_weather

    # both weather and icd must finish before dbt (dbt reads all raw tables)
    [ingest_weather, ingest_icd_codes] >> dbt_run
