WITH weather_with_region AS (
    SELECT
        w.weather_date,
        w.lat,
        w.lon,
        w.prcp,
        w.tavg,
        w.pres,
        r.region_key
    FROM {{ ref('stg_weather') }} w
    JOIN {{ ref('stg_organization_locations') }} ol
        ON ol.lat = w.lat AND ol.lon = w.lon
    JOIN {{ ref('stg_organizations') }} o
        ON o.organization_id = ol.organization_id
    JOIN {{ ref('dim_region') }} r
        ON r.city_name = o.city AND r.state_name = o.state
),

with_keys AS (
    SELECT
        wr.weather_date,
        wr.region_key,
        wr.prcp,
        wr.tavg,
        wr.pres,
        d.date_key,
        wc.weather_category_key
    FROM weather_with_region wr

    JOIN {{ ref('dim_date') }} d
        ON d.full_date = wr.weather_date

    LEFT JOIN {{ ref('dim_weather_category') }} wc
        ON wc.rain_flag IS NOT DISTINCT FROM (wr.prcp > 0)
        AND wc.temp_category IS NOT DISTINCT FROM CASE
            WHEN wr.tavg IS NULL THEN NULL
            WHEN wr.tavg < 0    THEN 'külm'
            WHEN wr.tavg < 10   THEN 'jahe'
            WHEN wr.tavg < 20   THEN 'soe'
            ELSE                     'kuum'
        END
        AND wc.pressure_category IS NOT DISTINCT FROM CASE
            WHEN wr.pres IS NULL THEN NULL
            WHEN wr.pres < 1000  THEN 'madal'
            WHEN wr.pres <= 1020 THEN 'normaalne'
            ELSE                      'kõrge'
        END
)

SELECT
    ROW_NUMBER() OVER (ORDER BY region_key, weather_date) AS weather_region_day_key,
    date_key,
    region_key,
    prcp        AS precipitation_mm,
    tavg        AS temperature_avg,
    pres        AS pressure_avg,
    prcp > 0    AS rainy_day_flag,
    weather_category_key
FROM with_keys
