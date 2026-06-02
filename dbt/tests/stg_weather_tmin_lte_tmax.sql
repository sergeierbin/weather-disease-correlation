-- Miinimumtemperatuur ei saa olla suurem kui maksimumtemperatuur — viitab Meteostat andmeveale.
-- severity: warn, sest viga on välises andmeallikas mida me kontrollida ei saa.
{{ config(severity='warn') }}

SELECT *
FROM {{ ref('stg_weather') }}
WHERE tmin > tmax
