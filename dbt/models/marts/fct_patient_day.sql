WITH condition_days AS (
    SELECT DISTINCT
        c.patient_id,
        c.onset_datetime::DATE AS onset_date,
        e.organization_id
    FROM {{ ref('stg_conditions') }} c
    JOIN {{ ref('stg_encounters') }} e ON e.encounter_id = c.encounter_id
    WHERE c.onset_datetime IS NOT NULL
),

with_keys AS (
    SELECT
        cd.patient_id,
        cd.onset_date,
        r.region_key,
        d.date_key,
        wc.weather_category_key
    FROM condition_days cd

    JOIN {{ ref('stg_organizations') }} o
        ON o.organization_id = cd.organization_id
    JOIN {{ ref('dim_region') }} r
        ON r.city_name = o.city AND r.state_name = o.state

    JOIN {{ ref('dim_date') }} d
        ON d.full_date = cd.onset_date

    LEFT JOIN {{ ref('stg_organization_locations') }} ol
        ON ol.organization_id = cd.organization_id
    LEFT JOIN {{ ref('stg_weather') }} w
        ON w.lat = ol.lat AND w.lon = ol.lon AND w.weather_date = cd.onset_date
    LEFT JOIN {{ ref('dim_weather_category') }} wc
        ON wc.weather_type IS NOT DISTINCT FROM CASE
            WHEN w.prcp > 0 AND w.pres_drop THEN 'vihm_rohulangusega'
            WHEN w.prcp > 0                 THEN 'vihm_ilma_rohulanguseta'
            ELSE                                 'kuiv_ilm'
        END
        AND wc.temp_category IS NOT DISTINCT FROM CASE
            WHEN w.tavg IS NULL THEN NULL
            WHEN w.tavg < 10    THEN 'külm'
            ELSE                     'soe'
        END
)

SELECT
    ROW_NUMBER() OVER (ORDER BY patient_id, onset_date, region_key) AS patient_day_key,
    patient_id,
    date_key,
    region_key,
    weather_category_key
FROM with_keys
