# TEHIK - Ilmastiku mõju haiguste esinemisele

##### Analysis correlation between weather conditions and diagnoses

### Sisukord
- [Äriküsimus](#äriküsimus)
- [Andmeallikad](#andmeallikad)
- [Arhitektuur](#arhitektuur)
- [Andmestik](#andmestik)
- [Riskid](#riskid)
- [Andmekvaliteedi testid](#andmekvaliteedi-testid)
- [Stack](#stack)
- [Käivitamine](#käivitamine)
- [Saladused ja konfiguratsioon](#saladused-ja-konfiguratsioon)
- [Projekti struktuur](#projekti-struktuur)
- [Kokkuvõte, puudused ja võimalikud edasiarendused](#kokkuvõte-puudused-ja-võimalikud-edasiarendused)
- [Meeskond](#meeskond)

### Äriküsimus

Küsimus: **"Kuidas erinevad ilmastikutingimused mõjutavad krooniliste ja/või valuga seotud haiguste esinemist erinevates piirkondades?"**

Projekti eesmärk on uurida, kuidas jaotuvad valuga seotud diagnoosid piirkonniti ning kas vihmastel ilmastikutingimustel võib olla seos kroonilise valu või liigesevalu diagnooside sagedasema esinemisega. Selleks analüüsitakse, kui palju esineb piirkonnas valudiagnoosiga patsiente ning kas vihmastel/madala õhurõhuga päevadel on nende patsientide arv suurem. Lisaks võrreldakse piirkondade lõikes vihmaste päevade osakaalu, et hinnata, kas ilmastikutingimuste ja vaadeldavate diagnooside vahel võib esineda seos.

**Mõõdikud**
1. Valuga seotud haiguste esinemissagedus 1000 patsiendi kohta Massachusettsi ja California piirkondades.
   - **Arvutusvalem:** valuga seotud haigussündmusega patsientide arv piirkonnas / kõigi patsientide arv piirkonnas * 1000

2. Valuga seotud haigustega patsientide osakaal ilmastikutüübi järgi (%).
   - **Arvutusvalem:** valuga seotud haigussündmusega patsientide arv antud ilmastikutüübis / kõigi patsientide arv antud ilmastikutüübis * 100
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

### Andmeallikad
1. Ilmastikuandmete API
2. SNOMED CT - ICD-10 maping excel tabelina
3. Sünteetilised terviseandmed HL7 FHIR andmevahetusstandardis [Synthea](https://github.com/synthetichealth/synthea)

### Arhitektuur
Arhitektuuri dokumentatsioon on koostatud mermaid diagrammi kasutades. 
Kujutatud on andmevoogu, kuidas andmete sissevõtt toimub ning kuidas transformatsioonidega on jõutud ärikihini. 
Projekti andmed oleme üles ehitanud täheskeemi põhimõttel, kus konteksti oleme toonud dimensiooni tabelitesse ja faktid faktitabelitesse. 

Projekti arhitektuur kujuneb [siin](docs/arhitektuur.md)  


### Andmestik

| Allikas                                     | Tüüp   | Ajas muutuv?                   | Roll          |
| ------------------------------------------- | ------ | ------------------------------ | ------------- |
| Ilmastikuandmed   | API  | Jah, päevas | Põhiandmevoog |
| SNOMED CT - ICD-10 maping | seed | Ei, staatiline | Kõrvaltabel   |
| Sünteetilised terviseandmed | seed |JAH, iga päev ?  | Kõrvaltabel   |

### Riskid

| Risk                                  | Mõju                                                                                                                                                                                                                                                  | Maandus                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sünteetiliste andmete kasutamise risk | Synthea on tõenäosuspõhine andmegeneraator. See tähendab, et reaalses elus eksisteerivat seost ei pruugi sünteetilised andmed peegeldada. Lõplik analüüs gold-kihis võib ekslikku või statistiliselt mitteolulist tulemust näidata.                   | Projekti eesmärk on andmetorustiku ja analüütika raamistiku töökindluse testimine, mitte meditsiinilise tõe välja selgitamine. Proovime disainida skaleeruva süsteemi, mida oleks võimalik ka reaalandmetega katsetada.                                                                                                                             |
| Käitumuslik nihe                      | Andmetes võib tekkida näiline negatiivne korrelatsioon valu ja halva ilma vahel -- sümptomid tegelikult ägenesid, aga registreeritud juhtumeid oli vähem.                                                                                             | Analüüsis kasutatakse onsetDateTime andmevälja (tegelik sümptomite algus), mitte arstivisiidi kuupäeva. See vähendab käitumusliku nihke mõju.                                                                                                                                                                                                       |
| Terminoloogia kaardistuse ebapiisavus | Kui patsiendil on haruldasem liigesehaigus või valudiagnoos, mille SNOMED kood ei ole referentstabelis esindatud, siis jääb see statistikast välja.  Erinevates piirkondades võivad arstid eelistada erinevaid SNOMED koode (regionaalne varieeruvus) | Tiimil on olemas kompetents, et kaardistada ära kõik olulisemad terminoloogia koodid, mis põhinevad SNOMED International ametlikul kaardistusel. Täiendavalt on võimalik luua andmekvaliteedi kontroll, mis logiks kõik Condition ressursi progresseeruva (recurrence) staatusega haigused eraldi tabelisse, kuid see ei kuulu praeguse töö skoopi. |

### Andmevoog lühidalt
1. Sissevõtt — projektis on kolm andmeallikat, igaühel oma sissevõtumeetod:
   1. **Sünteetilised terviseandmed (Synthea FHIR JSON)** Synthea genereerib ühe JSON-faili patsiendi kohta FHIR formaadis. Skript fetch_synthea.py loeb need failid kettalt, parsib ressursitüübid (Patient, Encounter, Organization, Condition) ja laadib need PostgreSQL raw-skeemi. Töödeldakse 100 faili kaupa (batch). Ainult eelnevalt määratud SNOMED koodidega seisundid ja visiidid imporditakse.
   2. **Ilmastikuandmed (Meteostat API)** Skript fetch_weather.py pärib iga haiguse tekkimise asukoha GPS-koordinaadid raw.organizations tabelist ning laadib vastava ajaperioodi ilmastikuandmed Meteostat teegi kaudu. Kasutatakse päevataseme (daily) mõõtmisi. Kui lähimas jaamas andmed puuduvad, suurendatakse otsinguraadiust (35 → 75 → 150 km).
   3. **ICD-10 / SNOMED koodide kaardistus (CSV)** Staatiline icd_snomed.csv fail laetakse fetch_icd_codes.py skriptiga tabelisse raw.icd10_codes. See on viitetabel, mis ei muutu.
   4. **Kõik kolm sissevõtuskripti on idempotentsed** — uuesti käivitamine ei tekita duplikaate (ON CONFLICT DO NOTHING). Andmete sissevõttu orkestreerib Airflow DAG (etl_pipeline). Synthea FHIR JSON-failid ja ICD-10 koodid laetakse paralleelselt, seejärel päritakse Meteostat API kaudu ilmaandmed kõigi asukohafailide koordinaatidele. DAG käivitub käsitsi (manuaalne trigger).
2. Laadimine — Andmed laaditakse staging kihti
   Airflow DAG laadib kõigepealt andmed `raw`-skeemi (kolm paralleelset sissevõtuskripti). Seejärel käivitab dbt staging kihi mudelid, mis loevad `raw`-tabelist ja loovad puhastatud vaated `staging`-skeemis.

   | Staging mudel | Raw allikas | Peamised muutused |
   |---|---|---|
   | `stg_patients` | `raw.patients` | `id` → `patient_id` |
   | `stg_encounters` | `raw.encounters` | veergude ümbernimetamine |
   | `stg_conditions` | `raw.conditions` | kõik diagnostikaväljad säilitatakse |
   | `stg_organizations` | `raw.organizations` | `id` → `organization_id` |
   | `stg_weather` | `raw.weather` | `NaN` → `NULL`; lisatakse `pres_prev` ja `pres_drop` (rõhu langus ≥5 ühikut) |
   | `stg_icd_codes` | `raw.icd10_codes` | ICD-10 / SNOMED kaardistus |

   Staging mudelid on dbt **vaated** (mitte tabelid) — andmeid ei kopeerita, SQL käivitatakse päringu ajal. Kõigil mudelitel on andmekvaliteedi testid (unikaalsus, not null, FK suhted).
3. Transformatsioon — dbt transformeerib `staging`-kihi andmed tähtskeemi (star schema) `marts`-kihiks.

   **Dimensioonitabelid (5 tk):**

   | Mudel | Allikas | Sisu |
   |---|---|---|
   | `dim_date` | `stg_conditions` | Kuupäevaspain haiguste alguskuupäevast tänaseni; `date_key` = YYYYMMDD |
   | `dim_patients` | `stg_patients` | Patsiendid; `patient_key` = MD5(patient_id) |
   | `dim_region` | `stg_organizations` | Asukohad koordinaatidega; `region_key` = MD5(organization_id) |
   | `dim_diagnosis` | `stg_icd_codes` | ICD-10 / SNOMED kaardistus; `diagnosis_key` = MD5(icd10_code \|\| snomed_code) |
   | `dim_weather_type` | `stg_weather` | Ilmatüüp: sademete ja rõhulanguse kombinatsioon + temperatuurivahemik (`külm`/`soe`) |

   **Faktitabelid (3 tk, kõik inkrementaalsed):**

   | Mudel | Granularsus | Peamised arvutused |
   |---|---|---|
   | `fct_patient_day` | patsient × päev × piirkond | haigussündmuste arv päevas; vihmasajupäeva lipp |
   | `fct_patient_weather_region` | üksik haigusseisund | iga diagnoos koos ilma- ja asukohakontekstiga |
   | `fct_weather_region_day` | piirkond × päev | ilmakokkuvõte piirkonniti: sademed, temperatuur, rõhk, rõhulanguse lipp |

   **Olulisemad arvutused:**
   - Surrogaatvõtmed: kõik dimensioonid ja faktid kasutavad MD5-räsi loomulikest võtmetest
   - Ilmastiku geograafiline sidumine: ilmaandmed seotakse patsientidega läbi `raw.organizations` koordinaatide (lat/lon)
   - Rõhulanguse lipp: arvutatakse staging-kihis — kui rõhk langes eelmisest päevast ≥5 hPa, on `pres_drop = TRUE`
4. Testimine — [Mitu] andmekvaliteedi testi kontrollivad korrektsust
5. Näidikulaud — [Kirjelda lühidalt, mida näidikulaud näitab]

### Andmekvaliteedi testid
Projekt kontrollib järgmist:

[Test 1 - ]
[Test 2 - ]
[Test 3 - ]
Testide tulemused: []

### Stack

| Komponent        | Tööriist   |
| ---------------- | ---------- |
| Sissevõtt        | Airflow  |
| Transformatsioon | dbt      |
| Andmehoidla      | PostgreSQL |
| Näidikulaud      | Superset |
| Orkestreerimine  | Airflow  |

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
- [Loetle, mis on lõpule viidud, mis töötab hästi]

**Puudused:**
- [Loetle ausalt, mis jäi tegemata - see ei mõjuta hinnet negatiivselt, vaid aitab hinnata]

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
| Sergei Erbin      | Tehniline stack    |
| Maria Kuusik      | Andmekvaliteet     |
| Kalder Maarand    | Transformatsioonid |
| Scharlett Hansson | Arhitektuur        |
