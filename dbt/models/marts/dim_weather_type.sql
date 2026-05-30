WITH categorized AS (
    SELECT DISTINCT
        CASE
            WHEN prcp > 0 AND pres_drop THEN 'vihm_rohulangusega'
            WHEN prcp > 0               THEN 'vihm_ilma_rohulanguseta'
            ELSE                             'kuiv_ilm'
        END AS weather_type,
        CASE
            WHEN tavg IS NULL THEN NULL
            WHEN tavg < 10    THEN 'külm'
            ELSE                   'soe'
        END AS temperature_band
    FROM {{ ref('stg_weather') }}
)

SELECT
    MD5(weather_type || '|' || COALESCE(temperature_band, '')) AS weather_type_key,
    weather_type IN ('vihm_rohulangusega', 'vihm_ilma_rohulanguseta') AS rain_flag,
    weather_type = 'vihm_rohulangusega'                               AS pressure_drop_flag,
    weather_type,
    temperature_band
FROM categorized
