# Edenemisraport

## Mis on valmis

-  [arhitektuur.md](/docs/arhitektuur.md) failis on kirjeldatud andmevoo diagramm, andmeallikad, täheskeemi realisatsioon ning faktitabelite granulaarsus
- [readme.md](/README.md) failis on kirjeldatud projektitöö äriküsimus, mõõdikud ehk tulevased visuaalid, andmeallikad, projekti struktuur, panustatav meeskond 
-  [docker-compose.yml](/docker-compose.yml) käivitab kõik teenused – Synthea, PostgreSQL, Airflow ja Superset.
- Andmed pärinevad kolmest allikast: patsiendid parsitakse [Synthea](https://github.com/synthetichealth/synthea/wiki/Basic-Setup-and-Running) genereeritud JSON-failidest, ilmaandmed [Meteostat API-st](https://meteostat.net/) ja kroonilised ning valuga seotud haigused [icd_snomed.csv-st](/ingestion/icd_snomed.csv).
- Andmed laaditakse staging-kihti: toored andmed ([patsiendid](/ingestion/fetch_synthea.py), [ilmaandmed](/ingestion/fetch_weather.py), [haigused](/ingestion/fetch_icd_codes.py)) laaditakse PostgreSQL raw-skeemi, kust need transformeeritakse [dbt staging-mudelitega raw_staging-skeemi](/dbt/models/staging/).
- Vähemalt üks transformatsioon toimib: transformatsioonid toimivad — dbt jooksutab edukalt 14 mudelit ([6 staging](/dbt/models/staging/) + [8 marts](/dbt/models/marts/)).
- Vähemalt üks näidikulaud on nähtaval: [Superset dashboard](/superset/dashboards/krooniliste_haiguste_ja_ilma_analuus.zip) on olemas 
- Vähemalt üks andmekvaliteedi test läbib: dbt käivitab 45 andmekvaliteedi testi (unikaalsus ja mitte-null, foreign key seosed) kõikide [staging](/dbt/models/staging/_models.yml) ja [marts](/dbt/models/marts/_models.yml) mudelite võtmeveergudel — kõik läbivad.


## Järgmised sammud

- Teise mõõdiku ülevaatus. Kas muudame ära mõõdiku või muudame ära tehnilise teostuse (vt ka "probleem 2").
- Otsus, kas jätame kolmanda mõõdiku hetkel skoobist välja või lahendame selle teistmoodi.
- Parandused andmemudelis
- Täiendavad andmekvaliteedi testid
- Kontrollime ja täiendame visuaalid

## Mis takistab

- Probleem 1 — kolmas mõõdik (Korduvate valuga seotud diagnooside osakaal (%) kombinatsioonis ilmastikutüübi ja rõhulangusega piirkonna lõikes) ei ole sünteetiliste andmetega planeeritud viisil teostatav, kuna selgus, et Syntheas ei ole kasutusel vastavaid staatuse väärtuseid (korduvate diagnooside kliinilised staatused "recurrence" ja "relapse"). Mõõdik ei ole sisuliselt vale, pärisandmetega peaks toimima (eeldusel et tervishoiutöötaja on korduvad diagnoosid korrektselt dokumenteerinud).
- Probleem 2 — teine mõõdik (Valuga seotud haigustega patsientide osakaal ilmastikutüübi järgi (%)) hetkel ei tööta, kuna sellist näitajat nagu "kõik patsiendid ühes ilmastikutüübis" hetkel meie projekti ülesehitus ei võimalda. Mõtleme uuel nädalal, mida sellega teeme.

## Kontrollpunkt

Käsk, millega saab kontrollida, et töövoog töötab:

```bash
docker compose exec postgres psql \
  -U postgres \
  -d etl_db \
  -c "
SELECT tabel, ridu FROM (
  SELECT 1 ord, 'raw.patients' AS tabel, COUNT(*) AS ridu FROM raw.patients
  UNION ALL SELECT 2, 'raw.conditions', COUNT(*) FROM raw.conditions
  UNION ALL SELECT 3, 'raw.weather', COUNT(*) FROM raw.weather
  UNION ALL SELECT 4, 'raw_marts.dim_patients', COUNT(*) FROM raw_marts.dim_patients
  UNION ALL SELECT 5, 'raw_marts.fct_patient_weather_region', COUNT(*) FROM raw_marts.fct_patient_weather_region
) t ORDER BY ord;
"
```

Oodatav tulemus:
- Kõik 5 tabelit on olemas ja ridu > 0 — andmed on liikunud allikast martsi
- raw.patients = raw_marts.dim_patients ehk kõik patsiendid jõudsid transformatsioonist läbi
- ilmaandmed on laaditud