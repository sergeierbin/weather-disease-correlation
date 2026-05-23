# ETL Project — Käivitusjuhend

## Esmakordne käivitamine

### 1. Kopeeri konfiguratsioon

```bash
cp .env.example .env
```

`.env` failis saab vajadusel muuta kasutajanimesid ja paroole ning Synthea parameetreid (patsientide arv, seed, osariigid).

### 2. Käivita Airflow ja Superset

```powershell
docker compose --profile tools run --rm airflow-init
docker compose --profile tools run --rm superset-init
```

`airflow-init` loob Airflow metaandmebaasi ja admini kasutaja.  
`superset-init` loob Superseti admini kasutaja ja impordib dashboardi automaatselt.

### 3. Käivita konteinerid

```powershell
docker compose up -d
```

Käivitab kõik konteinerid taustal — PostgreSQL, Airflow ja Superset.

### 4. Genereeri sünteetilised patsiendid (Synthea)

```powershell
docker compose --profile synthea run --rm synthea
```

Synthea parameetrid (patsientide arv, seed, osariigid) saab määrata `.env` failis.

Loob FHIR JSON failid kausta `synthea/output/fhir/`.

### 5. Käivita ETL pipeline

Ava Airflow UI aadressil http://localhost:8080:

1. Leia DAG nimega `etl_pipeline`
2. Klõpsa **Trigger DAG**

Superset dashboard on saadaval aadressil http://localhost:8088.

---

## Korduv käivitamine

Käivita Synthea andmete uuesti genereerimiseks. Sama seed-i korral lisatakse ainult uued read (inkrementaalne laadimine).

### 1. Genereeri sünteetilised patsiendid (Synthea)

```powershell
docker compose --profile synthea run --rm synthea
```

### 2. Käivita ETL pipeline

Ava Airflow UI aadressil http://localhost:8080:

1. Leia DAG nimega `etl_pipeline`
2. Klõpsa **Trigger DAG**

Superset dashboard on saadaval aadressil http://localhost:8088.

---

## Teenuste peatamine

Peatab kõik konteinerid.

```powershell
docker compose down
```

Kustutab kõik konteinerid koos andmetega (PostgreSQL, Airflow, Superset):

```powershell
docker compose down -v
```
