# TEHIK - Ilmastiku mõju haiguste esinemisele

##### Analysis correlation between weather conditions and diagnoses

### Sisukord
1. [Andmeallikad](#andmeallikad)
2. [Arhitektuur](#arhitektuur)
3. [Andmestik](#andmestik)
4. [Andmekvaliteet](#andmekvaliteedi-testid)
5. [Stack](#stack)
6. [Käivitamine](#käivitamine)
7. [Saladused ja konfiguratsioon](#saladused-ja-konfiguratsioon)
8. [Projekti struktuur](#projekti-struktuur)
9. [Kokkuvõte](#kokkuvõte-puudused-ja-võimalikud-edasiarendused)
10. [Meeskond](#meeskond)

### Äriküsimus

Küsimus: **"Kuidas jaotuvad enim levinud diagnoosid piirkonniti ning kas esineb statistiliselt oluline seos vihmaste ilmastikutingimuste ja kroonilise valu või liigesevalu diagnooside sagenemise vahel?"**

Projekti eesmärk on uurida, kuidas jaotuvad diagnoosid piirkonniti ning kas vihmastel ilmastikutingimustel võib olla seos kroonilise valu või liigesevalu diagnooside sagedasema esinemisega. Selleks analüüsitakse, millised diagnoosid on erinevates piirkondades kõige levinumad, kui palju esineb kroonilise valu või liigesevalu diagnoosiga patsiente ning kas vihmastel päevadel on nende patsientide arv piirkonniti suurem. Lisaks võrreldakse piirkondade lõikes vihmaste päevade osakaalu, et hinnata, kas ilmastikutingimuste ja vaadeldavate diagnooside vahel võib esineda seos.

**Mõõdikud**
1. Kroonilise valu või liigesevalu diagnoosiga patsientide arv piirkonniti  
    Patsientide arv igas piirkonnas, kellel esineb kroonilise valu või liigesevaluga seotud diagnoos.
2. Vihmastel päevadel kroonilise valu või liigesevalu diagnoosiga patsientide arv piirkonniti  
    Patsientide arv piirkondades, kus kroonilise valu või liigesevalu diagnoosiga patsiendid langevad kokku vihmaste päevadega valitud perioodil.
3. Vihmaste päevade osakaal piirkonniti (%)
4. Kas haiguste ägenemist mõjutab pigem vihm?
5. Kas temperatuuril või muudel teguritel on mingi mõju?

### Andmeallikad
1. Ilmastikuandmete API
2. WHO rahvusvaheliste haiguste klassifikaator  - [ICD-10](https://icd.who.int/icdapi)
3. Sünteetilised terviseandmed HL7 FHIR andmevahetusstandardis [Synthea](https://github.com/synthetichealth/synthea)

### Arhitektuur
Arhitektuuri dokumentatsioon on koostatud mermaid diagrammi kasutades. 
Kujutatud on andmevoogu, kuidas andmete sissevõtt toimub ning kuidas transformatsioonidega on jõutud ärikihini. 
Projekti andmed oleme üles ehitanud täheskeemi põhimõttel, kus konteksti oleme toonud dimensiooni tabelitesse ja faktid faktitabelitesse. 

Projekti arhitektuur kujuneb [siin](arhitektuur.md)  


### Andmestik

| Allikas | Tüüp | Ajas muutuv? | Roll |
|---------|------|--------------|------|
| Ilmastikuandmed | [API ] | Jah, [iga tund / päevas / muu] | Põhiandmevoog |
| WHO rahvusvaheliste haiguste klassifikaator | API | Ei, staatiline | Kõrvaltabel |
| Sünteetilised terviseandmed | [seed] | Ei, staatiline | Kõrvaltabel |


### Andmekvaliteedi testid

### Stack

| Komponent | Tööriist |
|-----------|---------|
| Sissevõtt | [Airflow] |
| Transformatsioon | [dbt] |
| Andmehoidla | PostgreSQL |
| Näidikulaud | [Superset] |
| Orkestreerimine | [Airflow] |

### Käivitamine

### Saladused ja konfiguratsioon

### Projekti struktuur
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
        └── etl_pipeline.py     # Orkestreerib kõik sammud õiges järjekorras
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


### Kokkuvõte, puudused ja võimalikud edasiarendused 

**Kokkuvõte:**
- [Loetle, mis on lõpule viidud, mis töötab hästi]

**Puudused:**
- [Loetle ausalt, mis jäi tegemata - see ei mõjuta hinnet negatiivselt, vaid aitab hinnata]

**Mis edasi:**
- [Mida tahaksid edasi teha, kui aega oleks rohkem]

### Meeskond

| Nimi | Roll |
|------|------|
| Sergei Erbin | [Tehniline stack] |
| Maria Kuusik | [Andmekvaliteet] |
| Kalder Maarand | [Transformatsioonid] |
| Scharlett Hansson | [Arhitektuur] |
