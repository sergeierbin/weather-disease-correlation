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

#### Esmakordne käivitamine codespaces ruumis või koduses arvutis
---

#### Eeltingimused

Pead installeerima:
- Docker ja Docker Compose
- Git

---

#### 1. Klooni ja seadista

```bash
git clone https://github.com/sergeierbin/weather-disease-correlation.git
cd weather-disease-correlation
cp .env.example .env
```

#### 2. Alusta teenuseid

```bash
docker compose --profile tools run --rm airflow-init
docker compose --profile tools run --rm superset-init
docker compose up -d
```

#### 3. Genereeri andmed

```bash
docker compose --profile synthea run --rm synthea
```

#### 4. Käivita pipeline

Ava http://localhost:8080, leia DAG `etl_pipeline` ja klõpsa **Trigger DAG**.

---

#### Teenused

- **Airflow:** http://localhost:8080 (admin/admin)
- **Superset:** http://localhost:8088 (admin/admin)

---

#### Teenuste peatamine

```bash
docker compose down
```


### Saladused ja konfiguratsioon

### Projekti struktuur
```
weather-disease-correlation/
│
├── .env                        # Päris credentials (ei lähe git'i)
├── .env.example                # Mall — täida ja kopeeri .env-iks
├── docker-compose.yml          # Kõik teenused: Postgres, Airflow, Superset, Synthea
├── RUNBOOK.md                  # Käivitusjuhend algusest lõpuni
├── andmekihid.md               # Andmemudeli kirjeldus kihtide kaupa
├── README.md                   # Projekti dokumentatsioon
│
├── docs/                       # Skeemid ja diagrammid
│   ├── arhitektuur.md          # Süsteemi arhitektuur
│   ├── ERdiagram.mmd           # Entity-Relationship diagramm
│   ├── andmevoo_flowchart.mmd  # Andmevoo visualiseerimine
│   ├── progressiraport.md      # Projekti edenemine
│   └── andmeallikad.mmd        # Andmeallikate skeem
│
├── postgres/
│   └── init.sql                # Loob raw skeemi ja tabelid
│
├── ingestion/                  # Python skriptid andmete laadimiseks raw skeemi
│   ├── icd_snomed.csv          # ICD-10 ↔ SNOMED koodide tabel (käsitsi koostatud)
│   ├── fetch_synthea.py        # FHIR JSON → raw.patients / encounters / conditions
│   ├── fetch_icd_codes.py      # icd_snomed.csv → raw.icd10_codes
│   ├── fetch_weather.py        # Meteostat → raw.weather; Open-Meteo → raw.organization_locations
│   └── utils/
│       ├── __init__.py
│       ├── db.py               # PostgreSQL ühenduse abifunktsioonid
│       └── codes.py            # Laadib TARGET_SNOMED_CODES icd_snomed.csv-st
│
├── dbt/                        # Andmete transformatsioon raw → staging → marts
│   ├── dbt_project.yml         # Projekti konfiguratsioon ja materaliseerimise reeglid
│   ├── profiles.yml            # Ühenduse seaded PostgreSQL-iga
│   └── models/
│       ├── staging/            # dbt vaated — puhastab ja nimetab raw andmed ümber
│       │   ├── _sources.yml
│       │   ├── _models.yml
│       │   ├── stg_patients.sql
│       │   ├── stg_encounters.sql
│       │   ├── stg_conditions.sql
│       │   ├── stg_organizations.sql
│       │   ├── stg_organization_locations.sql
│       │   ├── stg_weather.sql
│       │   └── stg_icd_codes.sql
│       │
│       └── marts/              # dbt tabelid — lõplik star schema analüüsiks
│           ├── _models.yml
│           ├── dim_patients.sql
│           ├── dim_diagnosis.sql
│           ├── dim_date.sql
│           ├── dim_region.sql
│           ├── dim_weather_category.sql
│           ├── fct_patient_day.sql
│           ├── fct_patient_weather_region.sql
│           └── fct_weather_region_day.sql
│
├── superset/
│   ├── init_superset.sh        # Seadistab Superseti ja impordib dashboardi
│   └── dashboards/
│       └── dashboard_export.zip
│
├── notebooks/
│   └── analüüs.ipynb           # Detailne andmeanalüüs
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

### Meeskond

| Nimi              | Roll               |
| ----------------- | ------------------ |
| Sergei Erbin      | Tehniline stack    |
| Maria Kuusik      | Andmekvaliteet     |
| Kalder Maarand    | Transformatsioonid |
| Scharlett Hansson | Arhitektuur        |
