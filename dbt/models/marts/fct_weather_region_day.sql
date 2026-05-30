{{ config(materialized='incremental', unique_key='weather_region_day_key') }}

WITH weather_with_region AS (
    SELECT
        w.weather_date,
        w.lat,
        w.lon,
        w.prcp,
        w.tavg,
        w.pres,
        w.pres_drop,
        r.region_key
    FROM {{ ref('stg_weather') }} w
    JOIN {{ ref('dim_region') }} r
        ON r.latitude = w.lat AND r.longitude = w.lon
),

with_keys AS (
    SELECT
        wr.weather_date,
        wr.region_key,
        wr.prcp,
        wr.tavg,
        wr.pres,
        wr.pres_drop,
        d.date_key,
        wc.weather_type_key
    FROM weather_with_region wr

    JOIN {{ ref('dim_date') }} d
        ON d.full_date = wr.weather_date

    LEFT JOIN {{ ref('dim_weather_type') }} wc
        ON wc.weather_type IS NOT DISTINCT FROM CASE
            WHEN wr.prcp > 0 AND wr.pres_drop THEN 'vihm_rohulangusega'
            WHEN wr.prcp > 0                   THEN 'vihm_ilma_rohulanguseta'
            ELSE                                    'kuiv_ilm'
        END
        AND wc.temperature_band IS NOT DISTINCT FROM CASE
            WHEN wr.tavg IS NULL THEN NULL
            WHEN wr.tavg < 10    THEN 'külm'
            ELSE                      'soe'
        END
)

SELECT
    MD5(region_key || '|' || weather_date::text) AS weather_region_day_key,
    weather_date,
    date_key,
    region_key,
    weather_type_key,
    prcp             AS precipitation_mm,
    tavg             AS temperature_avg_c,
    pres             AS pressure_avg_hpa,
    prcp > 0         AS rainy_day_flag,
    prcp = 0         AS clear_day_flag,
    pres_drop        AS pressure_drop_flag
FROM with_keys
{% if is_incremental() %}
WHERE weather_date > (SELECT MAX(weather_date) FROM {{ this }}) - INTERVAL '7 days'
{% endif %}
