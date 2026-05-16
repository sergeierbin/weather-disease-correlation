"""
ETL pipeline DAG — orchestrates the full data flow:

    fetch_synthea ──┐
                    ├──> fetch_weather ──┐
    fetch_icd_codes ┘                   ├──> dbt_run
                    ────────────────────┘

Steps:
  1. fetch_synthea   — parse FHIR JSON bundles → raw.patients / encounters / conditions
  2. fetch_icd_codes — pull WHO ICD-10 API     → raw.icd_codes         (runs in parallel with step 1)
  3. fetch_weather   — pull Meteostat API       → raw.weather           (needs patient coords from step 1)
  4. dbt_run         — run all dbt models       → staging / intermediate / marts
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# ── Default task settings ────────────────────────────────────────────────────

default_args = {
    "owner": "airflow",
    # Retry once after a 5-minute wait before marking the task as failed
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
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
    )

    # ── Step 2: ingest WHO ICD-10 codes ──────────────────────────────────────
    # Authenticates with the WHO ICD-10 API (OAuth2) and BFS-crawls all codes
    # into raw.icd_codes. Runs in parallel with ingest_synthea — no shared state.
    ingest_icd_codes = BashOperator(
        task_id="ingest_icd_codes",
        bash_command="python /opt/airflow/ingestion/fetch_icd_codes.py",
    )

    # ── Step 3: ingest Meteostat weather ─────────────────────────────────────
    # Groups patient home coordinates (rounded to 4 dp) from raw.encounters
    # and fetches daily weather for each location × date range via Meteostat.
    # Must run after ingest_synthea so patient coordinates are available.
    ingest_weather = BashOperator(
        task_id="ingest_weather",
        bash_command="python /opt/airflow/ingestion/fetch_weather.py",
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
            "--profiles-dir /opt/airflow/dbt"
        ),
    )

    # ── Task dependencies ─────────────────────────────────────────────────────
    # synthea must finish before weather (weather needs patient coords)
    ingest_synthea >> ingest_weather

    # both weather and icd must finish before dbt (dbt reads all raw tables)
    [ingest_weather, ingest_icd_codes] >> dbt_run
