# Edenemisraport

## Mis on valmis

-  [arhitektuur.md](/docs/arhitektuur.md) failis on kirjeldatud andmevoo diagramm, andmeallikad, täheskeemi realisatsioon ning faktitabelite granulaarsus
- [readme.md](/README.md) failis on kirjeldatud projektitöö äriküsimus, mõõdikud ehk tulevased visuaalid, andmeallikad, projekti struktuur, panustatav meeskond 
-  [docker-compose.yml](/docker-compose.yml) käivitab kõik teenused – Synthea, PostgreSQL, Airflow ja Superset.
- Andmed pärinevad kolmest allikast: patsiendid parsitakse Synthea genereeritud JSON-failidest, ilmaandmed Meteostat API-st ja kroonilised ning valuga seotud haigused [icd_snomed.csv-st](/ingestion/icd_snomed.csv).
- Andmed laaditakse staging-kihti: toored andmed laaditakse PostgreSQL raw-skeemi, kust need transformeeritakse dbt staging-mudelitega raw_staging-skeemi.
- Vähemalt üks transformatsioon toimib: transformatsioonid toimivad — dbt jooksutab edukalt 14 mudelit (6 staging + 8 marts).
- Vähemalt üks näidikulaud on nähtaval: Superset dashboard on olemas 
- Vähemalt üks andmekvaliteedi test läbib: dbt käivitab 26 andmekvaliteedi testi (unikaalsus ja mitte-null) kõikide staging ja marts mudelite võtmeveergudel — kõik läbivad.


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