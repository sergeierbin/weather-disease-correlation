WITH source AS (
    SELECT * FROM {{ source('raw', 'weather') }}
)

SELECT
    s.lat,
    s.lon,
    s.date  AS weather_date,
    s.tavg,
    s.tmin,
    s.tmax,
    s.prcp,
    s.pres,
    s.loaded_at,
    prev.pres                    AS pres_prev,
    prev.pres - s.pres >= 6      AS pres_drop
FROM source s
LEFT JOIN source prev
    ON  prev.lat  = s.lat
    AND prev.lon  = s.lon
    AND prev.date = s.date - INTERVAL '1 day'
