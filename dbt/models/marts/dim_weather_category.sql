WITH categorized AS (
    SELECT DISTINCT
        prcp > 0 AS rain_flag,

        CASE
            WHEN tavg IS NULL  THEN NULL
            WHEN tavg < 0      THEN 'külm'
            WHEN tavg < 10     THEN 'jahe'
            WHEN tavg < 20     THEN 'soe'
            ELSE                    'kuum'
        END AS temp_category,

        CASE
            WHEN pres IS NULL  THEN NULL
            WHEN pres < 1000   THEN 'madal'
            WHEN pres <= 1020  THEN 'normaalne'
            ELSE                    'kõrge'
        END AS pressure_category

    FROM {{ ref('stg_weather') }}
),

with_combined AS (
    SELECT
        rain_flag,
        temp_category,
        pressure_category,
        CONCAT_WS('-',
            CASE WHEN rain_flag THEN 'vihm' ELSE 'kuiv' END,
            temp_category,
            pressure_category
        ) AS combined_weather_type
    FROM categorized
)

SELECT
    ROW_NUMBER() OVER (ORDER BY rain_flag, temp_category, pressure_category) AS weather_category_key,
    rain_flag,
    temp_category,
    pressure_category,
    combined_weather_type
FROM with_combined
