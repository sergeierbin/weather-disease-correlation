-- Temperatuur väljaspool reaalset vahemikku viitab andmeveale (nt API veaväärtused -99 või 999).
SELECT *
FROM {{ ref('stg_weather') }}
WHERE tavg < -30 OR tavg > 50
