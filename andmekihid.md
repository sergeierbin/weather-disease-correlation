# Andmekihid

---

| Kiht | Tüüp | Kirjeldus |
|------|------|-----------|
| **0. Allikad** | failid / API-d | Synthea FHIR JSON, `icd_snomed.csv`, Open-Meteo geocoding API, Meteostat |
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

- **FirstName, MiddleName, LastName** — kas neid välju on analüüsis vaja? Kuna tegemist on sünteetiliste andmetega, siis nimed ei pruugi analüütiliselt lisaväärtust anda. Kas jätta välja?
- **Aadress** — kas täpne aadressirida on vajalik? Asukohaanalüüsiks piisab `city`, `state`, `lat` ja `lon` väljadest, mis meil juba olemas on. Kas täpne aadressirida on vajalik kui kasutame visiidiga seotud aadressi?
- **deceased_datetime** — võiksime selle jätta, kuna see võimaldab edaspidi analüüsida suremusega seotud mustreid.

### Organization tabel

- **Salvestamine** — salvestame ainult organisatsioonid, millele viitab vähemalt üks allesjäänud Encounter (kaudne filter SNOMED koodide kaudu).

Milliseid välju on vaja organisatsiooni ressursi kohta? Hetkel salvestame järgmised väljad:

- `id`
- `name` — organisatsiooni nimi
- `city` — linn
- `state` — osariik
- `type_code` — tüübi kood (nt `prov`)
- `type_display` — tüüp tekstina (nt `Healthcare Provider`)

### Encounter tabel

- **Salvestamine** — salvestame ainult kui on seotud kroonilise haiguse SNOMED koodiga (eraldi CSV).

Milliseid välju on vaja encounter ressursi kohta? Hetkel salvestame järgmised väljad:

- `encounter_id`
- `status`
- `class_code` — nt `AMB` (ambulatoorne)
- `type_code` — SNOMED protseduurikood
- `type_display` — visiidi tüüp tekstina
- `patient_id`
- `period_start` — visiidi algus
- `period_end` — visiidi lõpp
- `practitioner_display` — arsti nimi
- `location_display` — kliiniku/haigla nimi
- `service_provider_display` — organisatsiooni nimi tekstina
- `reason_code` — SNOMED põhjuse kood
- `reason_display` — põhjus tekstina
- `organization_id`

### Condition tabel

- **Salvestamine** — salvestame ainult kui on seotud kroonilise haiguse SNOMED koodiga (eraldi CSV).

Milliseid välju on vaja condition ressursi kohta? Hetkel salvestame järgmised väljad:

- `condition_id`
- `patient_id`
- `encounter_id` — nullable, mõned seisundid ei ole seotud konkreetse visiidiga
- `clinical_status` — nt `active`, `resolved`
- `verification_status` — nt `confirmed`
- `category_code` — nt `encounter-diagnosis`
- `condition_code` — SNOMED kood
- `condition_code_system` — kodeerimissüsteemi URI
- `condition_display` — haiguse nimi tekstina
- `onset_datetime` — millal seisund algas
- `recorded_date` — millal dokumenteeriti
- `abatement_datetime` — millal lõppes (NULL kui jätkub)

**Andmevoo skeem - kommentaarid:**
- Synthea andmed on skeemil kujutatud ressursside tasemel (Patient, Encounter, Organization, Condition), ilmaandmed aga väljade tasemel (sademed, temperatuur, õhuniikus, õhurõhk). Kas peaks olema sama graanulaarsus?
- Kas raw_regions skeemil on sama, mis raw.organization_locations?

---

## SNOMED CT - ICD-10

### ICD-10 / SNOMED koodide tabel

- **Allikas** — staatiline CSV fail `ingestion/icd_snomed.csv` (käsitsi koostatud)
- **Raw tabel** — `raw.icd10_codes`
- **Veerud** — `icd10_code`, `description_et`, `snomed_code`
- **Märkus** — kui ühel ICD-10 koodil on mitu SNOMED koodi, peab iga kood olema eraldi real (üks väärtus lahtris)

---

## Ilm

### Organization locations tabel

- **Allikas** — Open-Meteo geocoding API (otsing linna ja osariigi järgi)
- **Raw tabel** — `raw.organization_locations`
- **Veerud** — `organization_id`, `lat`, `lon`
- **Piirangud** — tasuta, ei nõua API võtit; mitte-äriline kasutus; limiit: 10 000 päringut/päev, 5 000/tund, 600/min
- **Märkus** — Synthea FHIR ei sisalda organisatsioonide geolocation laiendust (erinevalt patsientidest). Seetõttu ei ole võimalik koordinaate otse FHIR jsonist parsida ja geocoding on vajalik.

### Weather tabel

- **Allikas** — Meteostat (ajaloolised ilmaandmed koordinaatide ja kuupäeva järgi)
- **Raw tabel** — `raw.weather`
- **Veerud** — `lat`, `lon`, `date`, `tavg`, `tmin`, `tmax`, `prcp`, `pres`
- **Piirangud** — tasuta, ei nõua API võtit; andmed pärinevad ilmajaamadest, seega kaugete asukohtade jaoks võivad andmed puududa
- **Puuduvad väärtused** — osa kirjetest jääb tühjaks (tuleviku kuupäev või lähim ilmajaam liiga kauge). Kas puuduvad väärtused võiks pärida Open-Meteo archive API-st varuvariandina?
- **Küsimus** — kas õhuniiskus (`humidity`) on analüüsiks vajalik? Hetkel seda ei salvestata.

---

## Incrementaalsus

Synthea parameetrina on lisatud seedid. Kui käivitada Synthea uuesti sama seediga, genereerib see uued FHIR JSON failid samade patsientide kohta värskemate andmetega (uued visiidid, diagnooside uuendused). ETL laeb andmebaasi ainult uued sündmused juurde — duplikaadid ignoreeritakse (`ON CONFLICT DO NOTHING`). Samuti päritakse automaatselt juurde koordinaadid ja ilmaandmed uute visiitide kohta.

**Küsimus** — kas selline incrementaalne lahendus sobib?

Synthea käivitatakse kahe osariigi kohta eraldi, igaühel oma seed:
- `Massachusetts` → `SYNTHEA_SEED=12345`
- `California` → `SYNTHEA_SEED_2=12346`

Seedid on määratud `.env` failis ja `docker-compose.yml` kasutab neid eraldi käivitustes.

---

# 2. staging

## stg_patients

**Välja jäetud raw-st:**
- `loaded_at` — sisemise ingestioniga seotud metaandmed, analüüsiks ei ole vaja
- `first_name`, `middle_name`, `last_name` — jäetud välja juba raw tasemel (ingestionis), kuna sünteetilised nimed ei anna analüütiliselt lisaväärtust
- `address` — jäetud välja juba raw tasemel; asukohaanalüüsiks piisab `city`, `state`, `lat`, `lon` väljadest

**Alles jäetud:**
- `patient_id` (raw-s `id`)
- `birthdate`, `gender`
- `city`, `state`, `lat`, `lon`
- `deceased_datetime`

**Juurde arvutatud:**
- `is_deceased` — boolean, kas patsiendil on surma kuupäev
- `age_at_death` — vanus aastates surma hetkel; NULL kui patsient on elus

## stg_organizations

**Välja jäetud raw-st:**
- `loaded_at` — sisemise ingestioniga seotud metaandmed

**Alles jäetud:**
- `organization_id` (raw-s `id`)
- `name`, `city`, `state`
- `type_code`, `type_display`

**Juurde arvutatud:** puuduvad

## stg_conditions

**Välja jäetud raw-st:**
- `loaded_at` — sisemise ingestioniga seotud metaandmed
- `is_chronic` — kroonilisuse tuvastamiseks kasutatakse koodide loetelu (`icd_snomed.csv`), mitte abatement puudumist

**Alles jäetud:**
- `condition_id`, `patient_id`, `encounter_id`
- `clinical_status`, `verification_status`, `category_code`
- `condition_code`, `condition_code_system`, `condition_display`
- `onset_datetime`, `recorded_date`, `abatement_datetime`

**Juurde arvutatud:** puuduvad

## stg_organization_locations

**Välja jäetud raw-st:**
- `loaded_at` — sisemise ingestioniga seotud metaandmed

**Alles jäetud:**
- `organization_id`, `lat`, `lon`

**Juurde arvutatud:** puuduvad

## stg_icd_codes

**Välja jäetud raw-st:**
- `loaded_at` — sisemise ingestioniga seotud metaandmed

**Alles jäetud:**
- `icd10_code`, `description_et`, `snomed_code`

**Juurde arvutatud:** puuduvad

## stg_weather

**Välja jäetud raw-st:**
- `loaded_at` — sisemise ingestioniga seotud metaandmed
- `id` — raw tabelis sellist veergu ei ole; primary key on `(lat, lon, date)`

**Alles jäetud:**
- `lat`, `lon`
- `date` → `weather_date`
- `tavg`, `tmin`, `tmax`, `prcp`, `pres`

**Juurde arvutatud:** puuduvad

## stg_encounters

**Välja jäetud raw-st:**
- `loaded_at` — sisemise ingestioniga seotud metaandmed
- `duration_minutes` — ei ole analüüsiks vajalik

**Alles jäetud:**
- `encounter_id`, `patient_id`, `organization_id`
- `status`, `class_code`, `type_code`, `type_display`
- `period_start`, `period_end`
- `practitioner_display`, `location_display`, `service_provider_display`
- `reason_code`, `reason_display`

**Juurde arvutatud:** puuduvad

---

# 3. marts

## dim_patients

**Allikas:** `stg_patients`

**Väljad:**
- `patient_id`, `birthdate`, `gender`
- `city`, `state`, `lat`, `lon`
- `deceased_datetime`, `is_deceased`, `age_at_death`

**Võrreldes skeemiga:**
- Skeemil olid `FirstName`, `MiddleName`, `LastName` — jäetud välja raw tasemel (sünteetilised nimed ei anna analüütiliselt lisaväärtust)
- Skeemil oli `Address` — jäetud välja raw tasemel; asukohaanalüüsiks piisab `city`, `state`, `lat`, `lon`
- Skeemil oli `Id` tüübiga `int` — meil on `patient_id` tüübiga `text` (Synthea FHIR UUID)
- Skeemil puudusid: `city`, `state`, `lat`, `lon`, `deceased_datetime`, `is_deceased`, `age_at_death`

## dim_diagnosis

**Allikas:** `stg_icd_codes`

**Väljad:**
- `icd10_code`, `snomed_code`
- `description_et` → `diagnosis_name`

**Võrreldes skeemiga:**
- Skeemil oli `diagnosis_key` tüübiga `int` (surrogate key) — välja jäetud; looduslik võti on `(icd10_code, snomed_code)`

## dim_weather_category

**Allikas:** `stg_weather`

**Väljad:**
- `weather_category_key` — surrogate int PK (genereeritud `ROW_NUMBER()` abil)
- `rain_flag` — boolean, `prcp > 0`
- `temp_category` — `külm` (<0°C) / `jahe` (0–10°C) / `soe` (10–20°C) / `kuum` (>20°C)
- `pressure_category` — `madal` (<1000 hPa) / `normaalne` (1000–1020 hPa) / `kõrge` (>1020 hPa)
- `combined_weather_type` — kombinatsioon, nt `kuiv-soe-normaalne`

**Võrreldes skeemiga:**
- `humidity_category` — välja jäetud, kuna õhuniiskuse andmed puuduvad

## dim_date

**Allikas:** genereeritud (`GENERATE_SERIES`)

**Väljad:**
- `date_key` — surrogate int PK YYYYMMDD formaadis (nt `20240115`)
- `full_date` — täpne kuupäev
- `year`, `month`, `day`

**Vahemik:** esimese visiidi kuupäevast kuni tänaseni (dünaamiline)

## fct_patient_day

**Granulaarsus:** üks patsient ühel päeval ühes piirkonnas

**Väljad:**
- `patient_day_key` — surrogate int PK
- `patient_id` — FK → `dim_patients`
- `date_key` — FK → `dim_date`
- `region_key` — FK → `dim_region`
- `weather_category_key` — FK → `dim_weather_category`

**Lahtised küsimused:**

- **`active_condition_count`** — kuidas arvutada aktiivsete haiguste arvu konkreetsel päeval?
- **`pain_related_flag`** — kuidas tuvastada valuga seotud seisundid?

## fct_weather_region_day

**Granulaarsus:** üks päev ühes piirkonnas

**Väljad:**
- `weather_region_day_key` — surrogate int PK
- `date_key` — FK → `dim_date`
- `region_key` — FK → `dim_region`
- `precipitation_mm` (`prcp`)
- `temperature_avg` (`tavg`)
- `pressure_avg` (`pres`)
- `rainy_day_flag` — `prcp > 0`
- `weather_category_key` — FK → `dim_weather_category`

**Välja jäetud:**
- `humidity_avg` — õhuniiskuse andmed puuduvad Meteostat allikast (vt Weather tabel)

## fct_patient_weather_region

**Granulaarsus:** üks patsiendi haigussündmus kindlal kuupäeval kindlas piirkonnas

**Väljad:**
- `patient_weather_key` — surrogate int PK
- `patient_id` — FK → `dim_patients`
- `snomed_code` — FK → `dim_diagnosis` (looduslik võti, mitte surrogate int)
- `date_key` — FK → `dim_date` (visiidi kuupäev)
- `region_key` — FK → `dim_region`
- `encounter_id` — viide visiidile (tekst, mitte FK dim tabelile)
- `condition_start`, `condition_end` — seisundi algus- ja lõppkuupäev
- `pain_related_flag` — hetkel `NULL`, definitsioon on lahtine (vt lahtised küsimused)
- `rainy_day_flag` — `prcp > 0`
- `weather_category_key` — FK → `dim_weather_category`
- `condition_clinical` — kliiniline staatus (nt `active`, `resolved`)

## dim_region

**Allikas:** `stg_organizations` + `stg_organization_locations` (visiidi toimumise asukoht)

**Väljad:**
- `region_key` — surrogate int PK (genereeritud `ROW_NUMBER()` abil)
- `city_name`, `state_name`
- `latitude`, `longitude`

---

# Superset

## Seadistamine

**1. Andmebaasi ühendus** — `Settings → Database Connections → + Database`
- Vali: `PostgreSQL`
- Host: `postgres`, Port: `5432`, Database: `etl_db`
- Username: vaata `.env` faili (`POSTGRES_USER`)

**2. Datasettide import** — `Datasets → + Dataset`
- Vali skeem `raw_marts` ja impordi kõik 8 mart tabelit:
  `dim_date`, `dim_diagnosis`, `dim_patients`, `dim_region`, `dim_weather_category`, `fct_patient_day`, `fct_patient_weather_region`, `fct_weather_region_day`

## Graafikud

### Haigussündmused 1000 patsiendi kohta osariigi järgi

**Äriküsimus:** valuga seotud haiguste levimus 1000 patsiendi kohta Massachusettsi ja California piirkondades

**Valem:** (vähemalt ühe valuga seotud diagnoosiga patsientide arv / kõigi patsientide arv) × 1000

**Tüüp:** Bar Chart

**Allikas:** Virtual Dataset (`conditions_per_1000_by_state`)

```sql
WITH patients AS (
    SELECT *,
        CASE
            WHEN state = 'CA' THEN 'California'
            WHEN state = 'MA' THEN 'Massachusetts'
            ELSE state
        END AS state_name
    FROM raw_marts.dim_patients
)
SELECT
    state_name AS state,
    COUNT(DISTINCT fwr.patient_id)                                AS condition_patients,
    COUNT(DISTINCT p.patient_id)                                  AS patient_count,
    COUNT(DISTINCT fwr.patient_id)::float
        / NULLIF(COUNT(DISTINCT p.patient_id), 0) * 1000         AS conditions_per_1000
FROM patients p
LEFT JOIN raw_marts.fct_patient_weather_region fwr
    ON fwr.patient_id = p.patient_id
GROUP BY state_name
```

**Tulemus (praeguse valimiga):**
- California: 50 patsienti 1000-st
- Massachusetts: 103 patsienti 1000-st

### Valuga seotud haiguste levimus ilmastikutüübi järgi

**Äriküsimus:** kui suur osakaal patsientidest on valuga seotud haigustega erinevates ilmastikutingimustes osariigi lõikes

**Valem:** (valuga seotud haigustega patsientide arv / kõigi patsientide arv osariigis) × 100

**Tüüp:** Bar Chart

**Allikas:** Virtual Dataset (`conditions_pct_by_weather_type`)

**Seadistus:** X-telg: `weather_label`, Metriku: `MAX(pct)`, Dimensioon: `state_name`

```sql
WITH weather_labels AS (
    SELECT
        weather_category_key,
        CASE combined_weather_type
            WHEN 'kuiv-külm-normaalne'   THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-külm-kõrge'       THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-jahe-normaalne'   THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-jahe-kõrge'       THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-soe-normaalne'    THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-soe-kõrge'        THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-kuum-normaalne'   THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-kuum-kõrge'       THEN 'Stabiilne kuiv ilm'
            WHEN 'vihm-soe-normaalne'    THEN 'Soe ja vihmane'
            WHEN 'vihm-soe-kõrge'        THEN 'Soe ja vihmane'
            ELSE 'Muu'
        END AS weather_label
    FROM raw_marts.dim_weather_category
),
total_patients AS (
    SELECT
        CASE state WHEN 'CA' THEN 'California' WHEN 'MA' THEN 'Massachusetts' ELSE state END AS state_name,
        COUNT(DISTINCT patient_id) AS total
    FROM raw_marts.dim_patients
    GROUP BY state_name
),
condition_patients AS (
    SELECT
        wl.weather_label,
        CASE p.state WHEN 'CA' THEN 'California' WHEN 'MA' THEN 'Massachusetts' ELSE p.state END AS state_name,
        COUNT(DISTINCT fwr.patient_id) AS condition_patients
    FROM raw_marts.fct_patient_weather_region fwr
    JOIN weather_labels wl ON wl.weather_category_key = fwr.weather_category_key
    JOIN raw_marts.dim_patients p ON p.patient_id = fwr.patient_id
    GROUP BY wl.weather_label, state_name
)
SELECT
    c.weather_label,
    c.state_name,
    c.condition_patients,
    t.total AS total_patients,
    ROUND(c.condition_patients::numeric / NULLIF(t.total, 0) * 100, 1) AS pct
FROM condition_patients c
JOIN total_patients t ON t.state_name = c.state_name
ORDER BY c.weather_label, c.state_name
```

### Haigussündmused ilmastikutüübi järgi

**Äriküsimus:** haigussündmuste sagedus 1000 patsiendi kohta ilmastikutüübi, osariigi ja korduvuse lõikes

**Valem:** (sündmuste arv / kõigi patsientide arv osariigis) × 1000

**Tüüp:** Bar Chart

**Allikas:** Virtual Dataset (`conditions_by_weather_type`)

**Seadistus:** X-telg: `weather_label`, Metriku: `MAX(events_per_1000)`, Dimensioonid: `state_name`, `recurrence_type`

```sql
WITH weather_labels AS (
    SELECT
        weather_category_key,
        CASE combined_weather_type
            WHEN 'kuiv-külm-normaalne'   THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-külm-kõrge'       THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-jahe-normaalne'   THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-jahe-kõrge'       THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-soe-normaalne'    THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-soe-kõrge'        THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-kuum-normaalne'   THEN 'Stabiilne kuiv ilm'
            WHEN 'kuiv-kuum-kõrge'       THEN 'Stabiilne kuiv ilm'
            WHEN 'vihm-soe-normaalne'    THEN 'Soe ja vihmane'
            WHEN 'vihm-soe-kõrge'        THEN 'Soe ja vihmane'
            ELSE 'Muu'
        END AS weather_label
    FROM raw_marts.dim_weather_category
),
recurrence AS (
    SELECT
        patient_weather_key,
        patient_id,
        snomed_code,
        weather_category_key,
        CASE
            WHEN COUNT(*) OVER (PARTITION BY patient_id, snomed_code) > 1 THEN 'Korduv'
            ELSE 'Esmakordne'
        END AS recurrence_type
    FROM raw_marts.fct_patient_weather_region
),
total_patients AS (
    SELECT
        CASE state WHEN 'CA' THEN 'California' WHEN 'MA' THEN 'Massachusetts' ELSE state END AS state_name,
        COUNT(DISTINCT patient_id) AS total
    FROM raw_marts.dim_patients
    GROUP BY state_name
),
events AS (
    SELECT
        wl.weather_label,
        CASE p.state WHEN 'CA' THEN 'California' WHEN 'MA' THEN 'Massachusetts' ELSE p.state END AS state_name,
        r.recurrence_type,
        COUNT(r.patient_weather_key) AS event_count
    FROM recurrence r
    JOIN weather_labels wl ON wl.weather_category_key = r.weather_category_key
    JOIN raw_marts.dim_patients p ON p.patient_id = r.patient_id
    GROUP BY wl.weather_label, state_name, r.recurrence_type
)
SELECT
    e.weather_label,
    e.state_name,
    e.recurrence_type,
    e.event_count,
    t.total AS total_patients,
    ROUND(1000.0 * e.event_count / NULLIF(t.total, 0), 1) AS events_per_1000
FROM events e
JOIN total_patients t ON t.state_name = e.state_name
ORDER BY e.weather_label, e.state_name, e.recurrence_type
```

**Märkus:** `recurrence_type` klassifitseerib iga sündmuse — `Esmakordne` kui patsient esineb ühe diagnoosiga ainult üks kord, `Korduv` kui sama patsient-diagnoos kombinatsioon esineb rohkem kui üks kord.

---

## Nõuded, erisused ja küsimused analüütikule

### Graafik 1 — Haigussündmused 1000 patsiendi kohta osariigi järgi

**Algne nõue:**
> Valuga seotud haiguste esinemissagedus 1000 patsiendi kohta Massachusettsi ja California piirkondades.
> Arvutusvalem: (valuga seotud haigussündmusega patsientide arv piirkonnas / kõigi patsientide arv piirkonnas) / 1000

**Erisus:** Nõudes on valemis `/1000`, kuid epidemioloogiliselt korrektne on `×1000` — muidu tulemus oleks 0,05 (CA) ja 0,103 (MA), mis on mõttetult väike arv. Teostus kasutab `×1000`.

**Küsimus analüütikule:** Kas valemis on kirjaviga (`/1000` asemel `×1000`)?

---

### Graafik 2 — Valuga seotud haiguste levimus ilmastikutüübi järgi

**Algne nõue:**
> Vihmaste päevade osakaal piirkonniti (%)
> Arvutusvalem: (valuga seotud haigussündmusega patsientide arv antud ilmastikutüübis / kõigi patsientide arv antud ilmastikutüübis) / 100

**Erisused:**
1. **Pealkiri:** Nõudes "Vihmaste päevade osakaal" — kuid valem mõõdab *patsientide osakaalu*, mitte *päevade osakaalu*. Need on erinevad mõõdikud. Teostus kasutab pealkirja "Valuga seotud haiguste levimus ilmastikutüübi järgi".
2. **Valem:** Nõudes `/100`, kuid protsendi saamiseks peab kasutama `×100`. Kui jagada 100-ga, saaks tulemuseks 0,026, mitte 2,6%. Teostus kasutab `×100`.

**Küsimused analüütikule:**
- Kas graafiku pealkiri peaks olema "Vihmaste päevade osakaal" (nagu nõudes) või "Valuga seotud haiguste levimus ilmastikutüübi järgi" (nagu teostatud)? Algne pealkiri ei vasta valemile.
- Kas valemis on kirjaviga (`/100` asemel `×100`)?

---

### Graafik 3 — Haigussündmused ilmastikutüübi järgi

**Algne nõue:**
> Valuga seotud haiguste progresseerumine kombineeritud ilmastikutüüpide lõikes (külm ja rõske / soe ja vihmane / järsk õhurõhu langus / stabiilne kuiv ilm)
> Arvutusvalem:
> 1. valuga seotud haigussündmuse päevad vihmases ilmastikutüübis
> 2. Esinemissageduse arvutus: 1000 × punkt 1 tulem / kõigi patsientide arv
> 3. lisada piirkonna mõõtmed, eristades Massachusetts ja California
> 4. lisada kliinilise haigussündmuse mõõde, kus valuga seotud haigussündmused on klassifitseeritud korduvana

**Erisus:** Kategooria "Järsk õhurõhu langus" puudub. Praegune andmemudel salvestab ainult ühe päeva absoluutse õhurõhu väärtuse — rõhu muutuse (languse) arvutamiseks oleks vaja eelmise päeva väärtust, mida mudel ei salvesta.

**Küsimus analüütikule:** Kas "Järsk õhurõhu langus" kategooria on analüüsi jaoks oluline? Kui jah, tuleb andmemudelisse lisada eelmise päeva rõhu veerg (nt `lag(pres) OVER (PARTITION BY lat, lon ORDER BY date)`).

---

## Dashboard

**Nimi:** Krooniliste haiguste ja ilma analüüs

Dashboard on salvestatud ZIP failina ja imporditakse automaatselt esimesel käivitusel.


