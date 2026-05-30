# Andmekihid

---

| Kiht | Tüüp | Kirjeldus |
|------|------|-----------|
| **0. Allikad** | failid / API-d | Synthea FHIR JSON, `icd_snomed.csv`, Meteostat |
| **1. raw** | tabelid | Parsitud ja laaditud andmed PostgreSQL-i |
| **2. staging** | dbt vaated | Puhastatud ja ümber nimetatud veerud |
| **3. marts** | dbt tabelid | Lõplik star schema — Superset loeb siit |

**Märkus arhitektuuri kohta:** `staging` kiht on sisuliselt sarnane `raw` kihiga — mõlemad on toorkihid. See tuleneb dbt kasutamisest: dbt ei saa kirjutada otse `raw` skeemi peale marts mudeleid, vaid vajab vahekihti. Ilma dbt-ta saaks marts tabelid ehitada otse `raw` peale ja staging kiht poleks vajalik.

---

# 1. raw

> Tabelid on järjestatud FK sõltuvuste järgi — iga tabel peab olema loodud enne tabelit, mis sellele viitab.

## Synthea

### Patient tabel

- **Salvestamine** — salvestame kõik patsiendid.
- **Veerud:**
  - `id` — patsiendi ID
  - `state` — osariik (nt "MA", "CA")

### Organization tabel

- **Salvestamine** — salvestame ainult organisatsioonid, millele viitab vähemalt üks allesjäänud Encounter (kaudne filter SNOMED koodide kaudu).
- **Koordinaadid** — loetakse FHIR Location ressursist hospitalInformation bundlest (mitte geocoding API).
- **Veerud:**
  - `id`
  - `city` — linn
  - `state` — osariik
  - `lat` — laiuskraad (FHIR Location ressursist)
  - `lon` — pikkuskraad (FHIR Location ressursist)

### Encounter tabel

- **Salvestamine** — salvestame ainult kui on seotud kroonilise haiguse SNOMED koodiga (eraldi CSV).
- **Veerud:**
  - `encounter_id`
  - `patient_id`
  - `reason_code` — SNOMED põhjuse kood
  - `reason_display` — põhjus tekstina
  - `organization_id`

### Condition tabel

- **Salvestamine** — salvestame ainult kui on seotud kroonilise haiguse SNOMED koodiga (eraldi CSV).
- **Veerud:**
  - `condition_id`
  - `patient_id`
  - `encounter_id` — nullable, mõned seisundid ei ole seotud konkreetse visiidiga
  - `clinical_status` — nt `active`, `resolved`
  - `category_code` — nt `encounter-diagnosis`
  - `condition_code` — SNOMED kood
  - `condition_code_system` — kodeerimissüsteemi URI
  - `condition_display` — haiguse nimi tekstina
  - `onset_datetime` — millal seisund algas
  - `abatement_datetime` — millal lõppes (NULL kui jätkub)

---

## SNOMED CT - ICD-10

### ICD-10 / SNOMED koodide tabel

- **Allikas** — staatiline CSV fail `ingestion/icd_snomed.csv` (käsitsi koostatud)
- **Raw tabel** — `raw.icd10_codes`
- **Veerud** — `icd10_code`, `description_et`, `snomed_code`
- **Märkus** — kui ühel ICD-10 koodil on mitu SNOMED koodi, peab iga kood olema eraldi real

---

## Ilm

### Weather tabel

- **Allikas** — Meteostat (ajaloolised ilmaandmed koordinaatide ja kuupäeva järgi)
- **Raw tabel** — `raw.weather`
- **Veerud** — `lat`, `lon`, `date`, `tavg`, `tmin`, `tmax`, `prcp`, `pres`
- **Piirangud** — tasuta, ei nõua API võtit; andmed pärinevad ilmajaamadest, seega kaugete asukohtade jaoks võivad andmed puududa

---

## Incrementaalsus

Synthea parameetrina on lisatud seedid. Kui käivitada Synthea uuesti sama seediga, genereerib see uued FHIR JSON failid samade patsientide kohta värskemate andmetega. ETL laeb andmebaasi ainult uued sündmused juurde — duplikaadid ignoreeritakse (`ON CONFLICT DO NOTHING`).

Synthea käivitatakse kahe osariigi kohta eraldi, igaühel oma seed:
- `Massachusetts` → `SYNTHEA_SEED=12345`
- `California` → `SYNTHEA_SEED_2=12346`

---

# 2. staging

## stg_patients

- `patient_id` (raw-s `id`)
- `state`

## stg_organizations

- `organization_id` (raw-s `id`)
- `city`, `state`
- `lat`, `lon`

## stg_encounters

- `encounter_id`, `patient_id`, `organization_id`
- `reason_code`, `reason_display`

## stg_conditions

- `condition_id`, `patient_id`, `encounter_id`
- `condition_code`, `condition_display`, `clinical_status`
- `onset_datetime`, `abatement_datetime`

## stg_icd_codes

- `icd10_code`, `description_et`, `snomed_code`

## stg_weather

- `lat`, `lon`, `weather_date`
- `tavg`, `tmin`, `tmax`, `prcp`, `pres`
- `pres_prev` — eelmise päeva õhurõhk (LAG funktsioon)
- `pres_drop` — TRUE kui rõhk langes ≥6 hPa võrreldes eelmise päevaga

---

# 3. marts

## dim_patients

**Allikas:** `stg_patients`

- `patient_id`
- `state`

## dim_diagnosis

**Allikas:** `stg_icd_codes`

- `diagnosis_key` — surrogate PK
- `icd10_code`, `snomed_code`
- `diagnosis_name` (raw-s `description_et`)

## dim_weather_category

**Allikas:** `stg_weather`

- `weather_category_key` — surrogate PK
- `weather_type` — `vihm_rohulangusega` / `vihm_ilma_rohulanguseta` / `kuiv_ilm`
- `temp_category` — `külm` (<10°C) / `soe` (≥10°C) / NULL

## dim_date

**Allikas:** genereeritud (`GENERATE_SERIES`)

- `date_key` — surrogate PK (YYYYMMDD formaadis)
- `full_date`, `year`, `month`, `day`

**Vahemik:** esimese haiguse alguskuupäevast kuni tänaseni

## dim_region

**Allikas:** `stg_organizations`

- `region_key` — surrogate PK
- `city_name`, `state_name`
- `latitude`, `longitude`

## fct_patient_day

**Granulaarsus:** üks patsient ühel päeval ühes piirkonnas

- `patient_day_key` — surrogate PK
- `patient_id` — FK → `dim_patients`
- `date_key` — FK → `dim_date`
- `region_key` — FK → `dim_region`
- `weather_category_key` — FK → `dim_weather_category`

## fct_weather_region_day

**Granulaarsus:** üks päev ühes piirkonnas

- `weather_region_day_key` — surrogate PK
- `date_key` — FK → `dim_date`
- `region_key` — FK → `dim_region`
- `precipitation_mm`, `temperature_avg`, `pressure_avg`
- `rainy_day_flag`
- `weather_category_key` — FK → `dim_weather_category`

## fct_patient_weather_region

**Granulaarsus:** üks patsiendi haigussündmus kindlal kuupäeval kindlas piirkonnas

- `patient_weather_region_key` — surrogate PK
- `patient_key` — FK → `dim_patients`
- `diagnosis_key` — FK → `dim_diagnosis`
- `date_key` — FK → `dim_date`
- `region_key` — FK → `dim_region`
- `weather_type_key` — FK → `dim_weather_category`
- `condition_id`, `encounter_id`
- `onset_datetime`, `abatement_datetime`
- `pain_related_flag` — alati TRUE
- `occurrence_status` — `active` / `resolved`

---

# Superset

## Seadistamine

**1. Andmebaasi ühendus** — `Settings → Database Connections → + Database`
- Vali: `PostgreSQL`
- Host: `postgres`, Port: `5432`, Database: `etl_db`
- Username: vaata `.env` faili (`POSTGRES_USER`)

**2. Datasettide import** — `Datasets → + Dataset`
- Vali skeem `raw_marts` ja impordi mart tabelid

## Dashboard

**Nimi:** Krooniliste haiguste ja ilma analüüs

Dashboard on salvestatud ZIP failina (`superset/dashboards/`) ja imporditakse automaatselt esimesel käivitusel.
