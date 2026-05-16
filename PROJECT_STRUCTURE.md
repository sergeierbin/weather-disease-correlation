# ETL Project — Project Structure

```
etl_project/
│
├── .env                        # Päris credentials (ei lähe git'i)
├── .env.example                # Mall — täida ja kopeeri .env-iks
├── docker-compose.yml          # Kõik teenused: Postgres, Airflow, Superset, Synthea
├── RUNBOOK.md                  # Käivitusjuhend algusest lõpuni
├── PROGRESS.md                 # Sammude jälgimine
│
├── postgres/
│   └── init.sql                # Loob raw skeemi ja tabelid (patients, encounters,
│                               # conditions, weather, icd_codes)
│
├── synthea/
│   └── synthea-with-dependencies.jar   # Synthea käivitatav fail
│   └── output/fhir/            # Genereeritud FHIR JSON failid (gitignore'd)
│
├── ingestion/                  # Python skriptid andmete laadimiseks raw skeemi
│   ├── fetch_synthea.py        # FHIR JSON → raw.patients / encounters / conditions
│   ├── fetch_icd_codes.py      # WHO ICD-10 API → raw.icd_codes
│   ├── fetch_weather.py        # Meteostat API → raw.weather
│   └── utils/
│       ├── __init__.py
│       └── db.py               # PostgreSQL ühenduse abifunktsioonid
│
├── dbt/                        # Andmete transformatsioon raw → staging → marts
│   ├── dbt_project.yml         # Projekti konfiguratsioon ja materaliseerimise reeglid
│   ├── profiles.yml            # Ühenduse seaded PostgreSQL-iga
│   └── models/
│       ├── staging/            # Vaated (views) — puhastab raw andmed
│       │   ├── _sources.yml    # Registreerib raw tabeli allikad dbt jaoks
│       │   ├── stg_patients.sql
│       │   ├── stg_encounters.sql
│       │   ├── stg_conditions.sql
│       │   ├── stg_weather.sql
│       │   └── stg_icd_codes.sql
│       │
│       ├── intermediate/       # Vaated — ühendab tabeleid äriloogika jaoks
│       │   ├── int_patient_conditions.sql   # Patsiendid + diagnoosid
│       │   └── int_encounters_weather.sql   # Visiidid + ilm
│       │
│       └── marts/              # Tabelid — lõplik star schema analüüsiks
│           ├── fct_encounters.sql    # Faktitabel (visiit × diagnoos)
│           ├── dim_patients.sql      # Patsientide dimensioon
│           ├── dim_dates.sql         # Kuupäevade dimensioon
│           ├── dim_conditions.sql    # Diagnooside dimensioon
│           └── dim_weather.sql       # Ilmaandmete dimensioon
│
└── airflow/
    └── dags/
        └── etl_pipeline.py     # Orchestreerib kõik sammud õiges järjekorras
```

## Andmevoog

```
Synthea JAR → FHIR JSON failid
WHO API     ──────────────────→ raw skeem (PostgreSQL)
Meteostat   ──────────────────→      ↓
                                 dbt staging (views)
                                      ↓
                                 dbt intermediate (views)
                                      ↓
                                 dbt marts (tables) ← Superset loeb siit
```

## Andmebaasi skeemid

| Skeem | Tüüp | Kirjeldus |
|---|---|---|
| `raw` | tabelid | Laaditud andmed muutmata kujul |
| `staging` | vaated (views) | Puhastatud ja ümber nimetatud veerud |
| `intermediate` | vaated (views) | Tabelite ühendamine äriloogika jaoks |
| `marts` | tabelid | Lõplik star schema — Superset loeb siit |

## Star schema

```
                    dim_dates
                       │
dim_patients ── fct_encounters ── dim_conditions
                       │
                    dim_weather
```
