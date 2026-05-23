"""
ETL pipeline DAG — orchestrates the full data flow:

    fetch_synthea ──┐
                    ├──> fetch_weather ──┐
    fetch_icd_codes ┘                   ├──> dbt_run
                    ────────────────────┘

Steps:
  1. fetch_synthea   — parse FHIR JSON bundles → raw.patients / encounters / organizations / conditions
  2. fetch_icd_codes — load icd_snomed.csv       → raw.icd10_codes         (runs in parallel with step 1)
  3. fetch_weather   — geocode (Open-Meteo) + weather (Meteostat) → raw.organization_locations / raw.weather
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

    # ── Step 2: ingest ICD-10 / SNOMED mapping ───────────────────────────────
    # Loads ingestion/icd_snomed.csv into raw.icd10_codes.
    # Runs in parallel with ingest_synthea — no shared state.
    ingest_icd_codes = BashOperator(
        task_id="ingest_icd_codes",
        bash_command="python /opt/airflow/ingestion/fetch_icd_codes.py",
    )

    # ── Step 3: ingest weather ───────────────────────────────────────────────
    # Geocodes each organisation (Open-Meteo) → raw.organization_locations,
    # then fetches daily historical weather (Meteostat) → raw.weather.
    # Must run after ingest_synthea so encounters and organisations are available.
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
            "--profiles-dir /opt/airflow/dbt "
            "--log-path /tmp/dbt_logs "
            "--target-path /tmp/dbt_target"
        ),
    )

    # ── Task dependencies ─────────────────────────────────────────────────────
    # synthea must finish before weather (weather needs encounter + org data)
    ingest_synthea >> ingest_weather

    # both weather and icd must finish before dbt (dbt reads all raw tables)
    [ingest_weather, ingest_icd_codes] >> dbt_run
