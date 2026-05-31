WITH source AS (
    SELECT * FROM {{ source('raw', 'weather') }}
)

SELECT
    s.lat,
    s.lon,
    s.date  AS weather_date,
    NULLIF(s.tavg, 'NaN'::float) AS tavg,
    NULLIF(s.tmin, 'NaN'::float) AS tmin,
    NULLIF(s.tmax, 'NaN'::float) AS tmax,
    NULLIF(s.prcp, 'NaN'::float) AS prcp,
    NULLIF(s.pres, 'NaN'::float) AS pres,
    s.loaded_at,
    prev.pres                    AS pres_prev,
    prev.pres - s.pres >= 5      AS pres_drop
FROM source s
LEFT JOIN source prev
    ON  prev.lat  = s.lat
    AND prev.lon  = s.lon
    AND prev.date = s.date - INTERVAL '1 day'
