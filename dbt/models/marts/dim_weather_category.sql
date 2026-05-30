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
        END AS temp_category

    FROM {{ ref('stg_weather') }}
)

SELECT
    ROW_NUMBER() OVER (ORDER BY weather_type, temp_category) AS weather_category_key,
    weather_type,
    temp_category
FROM categorized
