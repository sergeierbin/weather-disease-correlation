WITH encounter_days AS (
    SELECT DISTINCT
        e.patient_id,
        e.period_start::DATE AS encounter_date,
        e.organization_id
    FROM {{ ref('stg_encounters') }} e
),

with_keys AS (
    SELECT
        ed.patient_id,
        ed.encounter_date,
        r.region_key,
        d.date_key,
        wc.weather_category_key
    FROM encounter_days ed

    JOIN {{ ref('stg_organizations') }} o
        ON o.organization_id = ed.organization_id
    JOIN {{ ref('dim_region') }} r
        ON r.city_name = o.city AND r.state_name = o.state

    JOIN {{ ref('dim_date') }} d
        ON d.full_date = ed.encounter_date

    LEFT JOIN {{ ref('stg_organization_locations') }} ol
        ON ol.organization_id = ed.organization_id
    LEFT JOIN {{ ref('stg_weather') }} w
        ON w.lat = ol.lat AND w.lon = ol.lon AND w.weather_date = ed.encounter_date
    LEFT JOIN {{ ref('dim_weather_category') }} wc
        ON wc.rain_flag IS NOT DISTINCT FROM (w.prcp > 0)
        AND wc.temp_category IS NOT DISTINCT FROM CASE
            WHEN w.tavg IS NULL THEN NULL
            WHEN w.tavg < 0    THEN 'külm'
            WHEN w.tavg < 10   THEN 'jahe'
            WHEN w.tavg < 20   THEN 'soe'
            ELSE                    'kuum'
        END
        AND wc.pressure_category IS NOT DISTINCT FROM CASE
            WHEN w.pres IS NULL THEN NULL
            WHEN w.pres < 1000  THEN 'madal'
            WHEN w.pres <= 1020 THEN 'normaalne'
            ELSE                    'kõrge'
        END
)

SELECT
    ROW_NUMBER() OVER (ORDER BY patient_id, encounter_date, region_key) AS patient_day_key,
    patient_id,
    date_key,
    region_key,
    weather_category_key
FROM with_keys
