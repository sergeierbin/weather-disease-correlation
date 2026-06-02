# TEHIK - Ilmastiku mõju haiguste esinemisele

##### Analysis correlation between weather conditions and diagnoses

### Sisukord
- [Äriküsimus](#äriküsimus)
- [Riskid](#riskid)
- [Arhitektuur](#arhitektuur)
- [Andmeallikad](#andmeallikad)
- [Andmestik](#andmestik)
- [Stack](#stack)
- [Käivitamine](#käivitamine)
- [Saladused ja konfiguratsioon](#saladused-ja-konfiguratsioon)
- [Andmevoog lühidalt](#andmevoog-lühidalt)
- [Andmekvaliteedi testid](#andmekvaliteedi-testid)
- [Projekti struktuur](#projekti-struktuur)
- [Kokkuvõte, puudused ja võimalikud edasiarendused](#kokkuvõte-puudused-ja-võimalikud-edasiarendused)
- [Meeskond](#meeskond)

### Äriküsimus

Küsimus: **"Kuidas erinevad ilmastikutingimused mõjutavad krooniliste ja/või valuga seotud haiguste esinemist erinevates piirkondades?"**

Projekti eesmärk on uurida, kuidas jaotuvad valuga seotud diagnoosid piirkonniti ning kas vihmastel ilmastikutingimustel võib olla seos kroonilise valu või liigesevalu diagnooside sagedasema esinemisega. Selleks analüüsitakse, kui palju esineb piirkonnas valudiagnoosiga patsiente ning kas vihmastel/madala õhurõhuga päevadel on nende patsientide arv suurem. Lisaks võrreldakse piirkondade lõikes vihmaste päevade osakaalu, et hinnata, kas ilmastikutingimuste ja vaadeldavate diagnooside vahel võib esineda seos.

**Mõõdikud**
1. Valuga seotud haigussündmuste arv Massachusettsi ja California piirkondades
   - **Arvutusvalem:** valuga seotud haigussündmusega patsientide arv piirkonnas (patient_id COUNT, kõikide ICD-10 diagnooside kohta MA ja CA piirkonnas)

2. Valuga seotud haigussündmustega patsientide arv kindlas ilmastikutüübis.
   - **Arvutusvalem:** valuga seotud haigussündmusega patsientide arv antud ilmastikutüübis 
   - Ilmastikutüübid, mille järgi on võimalik filtreerida:
     - vihm + rõhulangus
     - vihm ilma rõhulanguseta
     - kuiv ilm
     - sekundaarne dimensioon: temperatuur (näiteks külm/soe)

3. Korduvate valuga seotud diagnooside osakaal (%) kombinatsioonis ilmastikutüübi ja rõhulangusega piirkonna lõikes.
   - **Numerator:** korduvate valuga seotud diagnooside arv, kus `clinical_status` = `recurrence` või `relapse`. Viide: [FHIR Condition clinicalStatus loend](https://terminology.hl7.org/7.1.0/en/CodeSystem-condition-clinical.html)
   - **Denominator:** kõigi valuga seotud diagnooside arv sama rühma ja piirkonna sees
   - **Arvutusvalem:** korduvate osakaal (%) = numerator / denominator * 100
   - Rakendatakse iga ilmastikutüübi kohta:
     - vihm + rõhulangus
     - vihm ilma rõhulanguseta
     - kuiv ilm
     - sekundaarne dimensioon: temperatuur (näiteks külm/soe)
### Riskid

| Risk                                  | Mõju                                                                                                                                                                                                                                                  | Maandus                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sünteetiliste andmete kasutamise risk | Synthea on tõenäosuspõhine andmegeneraator. See tähendab, et reaalses elus eksisteerivat seost ei pruugi sünteetilised andmed peegeldada. Lõplik analüüs gold-kihis võib ekslikku või statistiliselt mitteolulist tulemust näidata.                   | Projekti eesmärk on andmetorustiku ja analüütika raamistiku töökindluse testimine, mitte meditsiinilise tõe välja selgitamine. Proovime disainida skaleeruva süsteemi, mida oleks võimalik ka reaalandmetega katsetada.                                                                                                                             |
| Käitumuslik nihe                      | Andmetes võib tekkida näiline negatiivne korrelatsioon valu ja halva ilma vahel -- sümptomid tegelikult ägenesid, aga registreeritud juhtumeid oli vähem.                                                                                             | Analüüsis kasutatakse onsetDateTime andmevälja (tegelik sümptomite algus), mitte arstivisiidi kuupäeva. See vähendab käitumusliku nihke mõju.                                                                                                                                                                                                       |
| Terminoloogia kaardistuse ebapiisavus | Kui patsiendil on haruldasem liigesehaigus või valudiagnoos, mille SNOMED kood ei ole referentstabelis esindatud, siis jääb see statistikast välja.  Erinevates piirkondades võivad arstid eelistada erinevaid SNOMED koode (regionaalne varieeruvus) | Tiimil on olemas kompetents, et kaardistada ära kõik olulisemad terminoloogia koodid, mis põhinevad SNOMED International ametlikul kaardistusel. Täiendavalt on võimalik luua andmekvaliteedi kontroll, mis logiks kõik Condition ressursi progresseeruva (recurrence) staatusega haigused eraldi tabelisse, kuid see ei kuulu praeguse töö skoopi. |


### Arhitektuur
Arhitektuuri dokumentatsioon on koostatud mermaid diagrammi kasutades. 
Kujutatud on andmevoogu, kuidas andmete sissevõtt toimub ning kuidas transformatsioonidega on jõutud ärikihini. 
Projekti andmed oleme üles ehitanud täheskeemi põhimõttel, kus konteksti oleme toonud dimensiooni tabelitesse ja faktid faktitabelitesse. 

Projekti arhitektuur kujuneb [siin](docs/arhitektuur.md)  

### Andmeallikad
1. Ilmastikuandmete API — [Meteostat](https://meteostat.net)
2. SNOMED CT - ICD-10 mapping CSV failina
3. Sünteetilised terviseandmed [HL7 FHIR R4](https://hl7.org/fhir/R4/) andmevahetusstandardis — [Synthea](https://github.com/synthetichealth/synthea)

### Andmestik

| Allikas                                     | Tüüp   | Ajas muutuv?                   | Roll          |
| ------------------------------------------- | ------ | ------------------------------ | ------------- |
| Sünteetilised terviseandmed | FHIR JSON | Jah (kui genereerida uusi Synthea faile) | Põhiandmevoog   |
| Ilmastikuandmed   | Meteostat API  | Jah, igapäevaselt | Põhiandmevoog |
| SNOMED CT - ICD-10 mapping | CSV | Ei, staatiline | Kõrvaltabel   |

### Stack

| Komponent           | Tööriist                             |
| ------------------- | ------------------------------------ |
| Sissevõtt           | Python ([Meteostat](https://meteostat.net), FHIR JSON parser) |
| Orkestreerimine     | [Apache Airflow](https://airflow.apache.org) |
| Transformatsioon    | [dbt](https://docs.getdbt.com)       |
| Andmehoidla         | [PostgreSQL](https://www.postgresql.org) |
| Konteineriseerimine | [Docker](https://www.docker.com)     |
| Näidikulaud         | [Apache Superset](https://superset.apache.org) |

### Käivitamine

#### Eeltingimused

- Docker Desktop
- Git

---

#### 1. Klooni ja seadista

```bash
git clone https://github.com/sergeierbin/weather-disease-correlation.git
cd weather-disease-correlation
cp .env.example .env
```

---

#### 2. Genereeri Synthea patsiendid

```bash
docker compose --profile synthea run --rm synthea
```

Laeb JAR-i (~150 MB) ja genereerib ~200 patsiendifaili. Võtab 2–3 minutit.

---

#### 3. Ehita ja käivita kogu stack

```bash
docker compose build
docker compose up -d
```

Käivitab automaatselt: PostgreSQL → Airflow init → Airflow → Superset init → Superset.
Oota ~2 minutit kuni kõik teenused käivituvad.

---

#### 4. Käivita ETL pipeline

Ava **Airflow**: http://localhost:8080 (admin / admin)
- Leia DAG `etl_pipeline`
- Vajuta ▶ (Trigger DAG)
- Oota ~10–15 minutit kuni kõik 4 taski rohelised

Ava **Superset**: http://localhost:8088 (admin / admin)
- Dashboard on automaatselt imporditud

Ava **dbt docs**: http://localhost:8081
- Andmemudeli lineage graaf ja dokumentatsioon
- Uueneb automaatselt iga DAG käivitusega

---

#### Kasulikud käsud

```bash
docker compose logs -f airflow-scheduler   # jälgi ETL kulgu
docker compose down                         # peata kõik
docker compose down -v                      # peata + kustuta andmed
docker compose down --remove-orphans        # peata + eemalda orb-konteinerid
```
### Saladused ja konfiguratsioon

Kõik saladused (paroolid, API võtmed, andmebaasi URL-id) on `.env` failis. Repos on ainult `.env.example`, mis näitab vajalike muutujate struktuuri ilma tegelike väärtusteta. Päris `.env` faili ei tohi GitHubi panna — see on `.gitignore`-s.

Vajalikud muutujad:

| Muutuja                     | Tähendus                            | Näide             |
| --------------------------- | ----------------------------------- | ----------------- |
| `POSTGRES_USER`             | PostgreSQL kasutajanimi             | `postgres`        |
| `POSTGRES_PASSWORD`         | PostgreSQL parool                   | (saladus)         |
| `POSTGRES_DB`               | Põhiandmebaasi nimi                 | `etl_db`          |
| `POSTGRES_PORT`             | PostgreSQL port                     | `5432`            |
| `AIRFLOW_FERNET_KEY`        | Airflow andmete krüpteerimise võti  | (genereerida)     |
| `AIRFLOW_SECRET_KEY`        | Airflow veebiserveri saladus        | (saladus)         |
| `AIRFLOW_WWW_USER_USERNAME` | Airflow UI kasutajanimi             | `admin`           |
| `AIRFLOW_WWW_USER_PASSWORD` | Airflow UI parool                   | (saladus)         |
| `SUPERSET_SECRET_KEY`       | Superset saladus                    | (saladus)         |
| `SUPERSET_ADMIN_USERNAME`   | Superset UI kasutajanimi            | `admin`           |
| `SUPERSET_ADMIN_PASSWORD`   | Superset UI parool                  | (saladus)         |
| `SYNTHEA_POPULATION`        | Genereeritavate patsientide arv     | `100`             |
| `SYNTHEA_STATE_1`           | Esimene osariik                     | `Massachusetts`   |
| `SYNTHEA_STATE_2`           | Teine osariik                       | `California`      |
| `FHIR_LIMIT`                | Maksimaalne parsitavate failide arv | `0` (piiranguta)  |
| `AIRFLOW_ALERT_EMAIL`       | E-post tõrketeadeteks (valikuline)  | (tühi = keelatud) |


### Andmekvaliteedi testid
Projekt kontrollib järgmist:

[Test 1 - ]
[Test 2 - ]
[Test 3 - ]
Testide tulemused: []

### Näidikulaud

### Projekti struktuur
```
weather-disease-correlation/
│
├── .env                        # Päris credentials (ei lähe git'i)
├── .env.example                # Mall — täida ja kopeeri .env-iks
├── .gitattributes              # Ühtlased reavahetused (LF)
├── docker-compose.yml          # Kõik teenused: Postgres, Airflow, Superset, Synthea
├── README.md                   # Projekti dokumentatsioon
│
├── .vscode/
│   └── settings.json           # VS Code seaded (T-SQL linter keelatud dbt jaoks)
│
├── docs/                       # Skeemid ja diagrammid
│   ├── arhitektuur.md          # Süsteemi arhitektuur
│   ├── progressiraport.md      # Projekti edenemine
│   └── Mõõdikud - Tulemused.md
│
├── docker/
│   └── airflow/
│       └── Dockerfile          # Kohandatud Airflow image (dbt + meteostat sisse küpsetatud)
│
├── postgres/
│   └── init.sql                # Loob skeemid, tabelid ja indeksid
│
├── ingestion/                  # Python skriptid andmete laadimiseks raw skeemi
│   ├── icd_snomed.csv          # ICD-10 ↔ SNOMED koodide tabel (käsitsi koostatud)
│   ├── fetch_synthea.py        # FHIR JSON → raw.patients / encounters / conditions
│   ├── fetch_icd_codes.py      # icd_snomed.csv → raw.icd10_codes
│   ├── fetch_weather.py        # Meteostat → raw.weather
│   └── utils/
│       ├── db.py               # PostgreSQL ühenduse abifunktsioonid
│       └── codes.py            # Laadib TARGET_SNOMED_CODES icd_snomed.csv-st
│
├── dbt/                        # Andmete transformatsioon raw → staging → marts
│   ├── dbt_project.yml         # Projekti konfiguratsioon ja materaliseerimise reeglid
│   ├── profiles.yml            # Ühenduse seaded PostgreSQL-iga
│   └── models/
│       ├── staging/            # dbt vaated — puhastab ja nimetab raw andmed ümber
│       │   ├── _sources.yml    # Allikate definitsioonid + freshness testid
│       │   ├── _models.yml
│       │   ├── stg_patients.sql
│       │   ├── stg_encounters.sql
│       │   ├── stg_conditions.sql
│       │   ├── stg_organizations.sql
│       │   ├── stg_weather.sql
│       │   └── stg_icd_codes.sql
│       │
│       └── marts/              # dbt inkrementaalsed tabelid — star schema analüüsiks
│           ├── _models.yml     # Andmekvaliteedi testid (unique, not_null, relationships)
│           ├── dim_patients.sql
│           ├── dim_diagnosis.sql
│           ├── dim_date.sql
│           ├── dim_region.sql
│           ├── dim_weather_type.sql
│           ├── fct_patient_day.sql
│           ├── fct_patient_weather_region.sql
│           └── fct_weather_region_day.sql
│
├── dbt/tests/                  # Kohandatud SQL andmekvaliteedi testid
│   ├── stg_conditions_abatement_after_onset.sql
│   ├── stg_weather_prcp_not_negative.sql
│   └── stg_weather_tavg_valid_range.sql
│
├── tests/                      # pytest unit testid
│   ├── test_fetch_synthea.py
│   └── test_fetch_weather.py
│
├── superset/
│   ├── init_superset.sh        # Seadistab Superseti ja impordib dashboardi
│   └── dashboards/
│       └── krooniliste_haiguste_ja_ilma_analuus.zip
│
└── airflow/
    └── dags/
        └── etl_pipeline.py     # Orkestreerib kõik sammud õiges järjekorras
```


### Kokkuvõte, puudused ja võimalikud edasiarendused 

**Kokkuvõte:**
- Synthea genereerib sünteetilised terviseandmed FHIR R4 formaadis
- Kolm sissevõtuskripti töötavad: Synthea FHIR JSON parsimine, Meteostat ilmaandmete pärimine ja ICD-10/SNOMED CSV laadimine — kõik idempotentsed
- Airflow DAG orkestreerib kogu andmevoo (sissevõtt → ilm → dbt) õiges järjekorras
- dbt staging kiht (6 mudelit) puhastab ja standardiseerib kõik toored andmed
- dbt marts kiht: 5 dimensioonitabelit + 3 faktitabelit tähtskeemina
- Inkrementaalne laadimine faktitabelites (`loaded_at`-põhine filter)
- Ilmastikuandmete geograafiline sidumine patsiendiandmetega lat/lon kaudu
- Rõhulanguse (`pres_drop`) ja ilmatüübi (`dim_weather_type`) klassifikatsioon
- Andmekvaliteedi testid: ...
- dbt docs genereeritakse automaatselt pärast iga käivitust
- Superset näidikulaud visualiseerib tulemusi

**Puudused:**
- Kolmas mõõdik (Korduvate valuga seotud diagnooside osakaal (%) kombinatsioonis ilmastikutüübi ja rõhulangusega piirkonna lõikes) ei ole sünteetiliste andmetega planeeritud viisil teostatav, kuna selgus, et Syntheas ei ole kasutusel vastavaid staatuse väärtuseid (korduvate diagnooside kliinilised staatused "recurrence" ja "relapse"). Mõõdik ei ole sisuliselt vale, pärisandmetega peaks toimima (eeldusel et tervishoiutöötaja on korduvad diagnoosid korrektselt dokumenteerinud).
[Loetle ausalt, mis jäi tegemata - see ei mõjuta hinnet negatiivselt, vaid aitab hinnata]

**Mis edasi:**
- [Mida tahaksid edasi teha, kui aega oleks rohkem]
- **Synthea genereeritud JSON-failide parsimise optimeerimine ja inkrementaalse laadimise ajastamine**
  - Kaaluda stsenaariumid:
   1. **Tingimuslik parsimine** — genereerida uusi JSON-faile Synthea abil vastavalt vajadusele ning enne parsimist kontrollida, kas fail on uuendatud; parsida ainult muutunud failid. See võiks tõsta parsimise kiirust oluliselt.
   2. **Tulevikusündmustega failid** — genereerida Synthea JSON-failid ka tuleviku sündmustega ning parsida igapäevaselt ainult tänaseks toimunud sündmusi. See võimaldaks ajastada igapäevast inkrementaalset laadimist. Reaalses elus ei ole see siiski praktiline, kuna sündmused ei ole ette teada. Praktikas on tavaliselt saadaval API, kust saab pärida ainult uusi sündmusi — sellisel juhul ei ole parsimine niivõrd mahukas. Sel juhul ei saa rakendada eelmises punktis mainitud tingimusliku parsimist, kuna failid ei uueneks.
  3. **Paralleelne parsimine** — suurendada korraga parsitavate failide arvu ja katsetada paralleelseid protsesse. Selle mõju oleks tõenäoliselt minimaalne.
- **Praeguse marts-kihi muutmine intermediate-kihiks ja Superseti virtuaalsete dataset'ide kihi muutmine marts-kihiks.**

### Meeskond

| Nimi              | Roll               |
| ----------------- | ------------------ |
| Sergei Erbin      | E2E Andmetoru arendamine (Claude Code abiga) |
| Maria Kuusik      | Andmekvaliteet     |
| Kalder Maarand    | Transformatsioonid |
| Scharlett Hansson | Arhitektuur        |

