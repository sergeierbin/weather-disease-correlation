-- Sademed ei saa olla negatiivsed. Negatiivne väärtus viitab andmeveale ilmaandmete API-s või töötluses.
SELECT *
FROM {{ ref('stg_weather') }}
WHERE prcp < 0
