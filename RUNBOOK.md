# ETL Project — Runbook

## First-time setup

### 1. Environment variables

```powershell
copy .env.example .env
```

Edit `.env` and fill in all values:

```
POSTGRES_USER=etl_user
POSTGRES_PASSWORD=etl_password_dev
POSTGRES_DB=etl_db
POSTGRES_PORT=5432
AIRFLOW_DB=airflow_db

# Generate Fernet key:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
AIRFLOW_FERNET_KEY=<generated key>
AIRFLOW_SECRET_KEY=<any long random string>
AIRFLOW_WWW_USER_USERNAME=admin
AIRFLOW_WWW_USER_PASSWORD=admin

SUPERSET_SECRET_KEY=<any long random string>
SUPERSET_ADMIN_USERNAME=admin
SUPERSET_ADMIN_PASSWORD=admin

SYNTHEA_POPULATION=100

# Register at https://icd.who.int/icdapi
ICD_CLIENT_ID=<WHO API client ID>
ICD_CLIENT_SECRET=<WHO API client secret>
```

### 2. Start PostgreSQL

```powershell
docker compose up -d postgres
```

### 3. Generate synthetic patients (Synthea)

```powershell
docker compose --profile synthea run --rm synthea
```

Produces FHIR JSON bundles in `synthea/output/fhir/`.

### 4. Initialise Airflow (run once)

```powershell
docker compose --profile tools run --rm airflow-init
```

Creates the Airflow metadata database and the admin user.

### 5. Start Airflow

```powershell
docker compose up -d airflow-webserver airflow-scheduler
```

UI available at http://localhost:8080 — log in with the credentials from `.env`.

### 6. Initialise and start Superset (run init once)

```powershell
docker compose --profile tools run --rm superset-init
docker compose up -d superset
```

UI available at http://localhost:8088.

### 7. Trigger the ETL pipeline

In the Airflow UI (http://localhost:8080):

1. Find the DAG named `etl_pipeline`
2. Click **Trigger DAG**
3. The DAG runs tasks in this order:

```
ingest_synthea ──┐
                 ├──> ingest_weather ──┐
ingest_icd_codes ┘                    ├──> dbt_run
                 ─────────────────────┘
```

---

## Subsequent runs

Run this when you want to regenerate Synthea data and reload everything:

```powershell
docker compose --profile synthea run --rm synthea
# Then trigger the DAG again from the Airflow UI
```

---

## Stop all services

```powershell
docker compose down
```

To also delete all stored data (PostgreSQL, Airflow, Superset volumes):

```powershell
docker compose down -v
```
