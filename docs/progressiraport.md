# Edenemisraport

## Mis on valmis

-  [arhitektuur.md](/docs/arhitektuur.md) failis on kirjeldatud andmevoo diagramm, andmeallikad, täheskeemi realisatsioon ning faktitabelite granulaarsus
- [readme.md](/README.md) failis on kirjeldatud projektitöö äriküsimus, mõõdikud ehk tulevased visuaalid, andmeallikad, projekti struktuur, panustatav meeskond 
-  [docker-compose.yml](/docker-compose.yml) käivitab kõik teenused – Synthea, PostgreSQL, Airflow ja Superset.
- Andmed pärinevad kolmest allikast: patsiendid parsitakse [Synthea](https://github.com/synthetichealth/synthea/wiki/Basic-Setup-and-Running) genereeritud JSON-failidest, ilmaandmed [Meteostat API-st](https://meteostat.net/) ja kroonilised ning valuga seotud haigused [icd_snomed.csv-st](/ingestion/icd_snomed.csv).
- Andmed laaditakse staging-kihti: toored andmed ([patsiendid](/ingestion/fetch_synthea.py), [ilmaandmed](/ingestion/fetch_weather.py), [haigused](/ingestion/fetch_icd_codes.py)) laaditakse PostgreSQL raw-skeemi, kust need transformeeritakse [dbt staging-mudelitega raw_staging-skeemi](/dbt/models/staging/).
- Vähemalt üks transformatsioon toimib: transformatsioonid toimivad — dbt jooksutab edukalt 14 mudelit ([6 staging](/dbt/models/staging/) + [8 marts](/dbt/models/marts/)).
- Vähemalt üks näidikulaud on nähtaval: [Superset dashboard](/superset/dashboards/krooniliste_haiguste_ja_ilma_analuus.zip) on olemas 
- Vähemalt üks andmekvaliteedi test läbib: dbt käivitab 26 andmekvaliteedi testi (unikaalsus ja mitte-null) kõikide [staging](/dbt/models/staging/_models.yml) ja [marts](/dbt/models/marts/_models.yml) mudelite võtmeveergudel — kõik läbivad.


## Järgmised sammud

- [Esimene tegevus, mis ees ootab]
- [Teine tegevus]
- [Kolmas tegevus]

## Mis takistab

- [Probleem 1 — näiteks: API tagastab vigaseid väärtusi ühes linnas]
- [Probleem 2 — või: "Praegu pole blokeerivaid probleeme"]

## Kontrollpunkt

Käsk, millega saab kontrollida, et töövoog töötab:

```bash
# [Lisa siia käsk, mis näitab, et andmed liiguvad allikast näidikulauani]
# Näiteks:
docker compose exec pipeline python scripts/run_pipeline.py check
```

Oodatav tulemus: [Kirjelda, mida töötav süsteem väljastab]