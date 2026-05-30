WITH source AS (
    SELECT * FROM {{ source('raw', 'weather') }}
),

with_prev_pressure AS (
    SELECT
        lat,
        lon,
        date  AS weather_date,
        tavg,
        tmin,
        tmax,
        prcp,
        pres,
        LAG(pres) OVER (PARTITION BY lat, lon ORDER BY date) AS pres_prev
    FROM source
)

SELECT
    lat,
    lon,
    weather_date,
    tavg,
    tmin,
    tmax,
    prcp,
    pres,
    pres_prev,
    pres_prev - pres >= 6 AS pres_drop
FROM with_prev_pressure
