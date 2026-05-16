-- Dimension table: daily weather observations per location.
-- Grain: (lat, lon, weather_date) — unique combination
-- Used by: fct_encounters (joined on lat + lon + date for correlation analysis)

WITH source AS (
    SELECT * FROM {{ ref('stg_weather') }}
)

SELECT
    weather_id,
    lat,
    lon,
    weather_date,
    tavg,
    tmin,
    tmax,
    prcp,
    pres,

    -- Categorise rain intensity for easier filtering in Superset
    CASE
        WHEN prcp IS NULL  THEN 'Unknown'
        WHEN prcp = 0      THEN 'Dry'
        WHEN prcp < 2.5    THEN 'Light rain'
        WHEN prcp < 7.6    THEN 'Moderate rain'
        ELSE                    'Heavy rain'
    END AS rain_category,

    -- Categorise temperature for easier grouping
    CASE
        WHEN tavg IS NULL  THEN 'Unknown'
        WHEN tavg < 0      THEN 'Freezing'
        WHEN tavg < 10     THEN 'Cold'
        WHEN tavg < 20     THEN 'Mild'
        ELSE                    'Warm'
    END AS temp_category

FROM source
