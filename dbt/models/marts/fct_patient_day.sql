{{ config(materialized='incremental', unique_key='patient_day_key') }}

WITH condition_days AS (
    SELECT
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
        cd.organization_id,
        p.patient_key,
        r.region_key,
        d.date_key,
        w.prcp,
        wc.weather_type_key
    FROM condition_days cd

    JOIN {{ ref('dim_patients') }} p
        ON p.source_patient_id = cd.patient_id
    JOIN {{ ref('dim_region') }} r
        ON r.organization_id = cd.organization_id
    JOIN {{ ref('dim_date') }} d
        ON d.full_date = cd.onset_date
    LEFT JOIN {{ ref('stg_weather') }} w
        ON w.lat = r.latitude AND w.lon = r.longitude AND w.weather_date = cd.onset_date
    LEFT JOIN {{ ref('dim_weather_type') }} wc
        ON wc.weather_type IS NOT DISTINCT FROM CASE
            WHEN w.prcp > 0 AND w.pres_drop THEN 'vihm_rohulangusega'
            WHEN w.prcp > 0                 THEN 'vihm_ilma_rohulanguseta'
            ELSE                                 'kuiv_ilm'
        END
        AND wc.temperature_band IS NOT DISTINCT FROM CASE
            WHEN w.tavg IS NULL THEN NULL
            WHEN w.tavg < 10    THEN 'külm'
            ELSE                     'soe'
        END
),

aggregated AS (
    SELECT
        patient_key,
        onset_date,
        region_key,
        date_key,
        MAX(weather_type_key)  AS weather_type_key,
        COUNT(*)               AS disease_event_count,
        BOOL_OR(prcp > 0)      AS rainy_day_flag
    FROM with_keys
    GROUP BY patient_key, onset_date, region_key, date_key
)

SELECT
    MD5(patient_key::text || '|' || onset_date::text || '|' || region_key::text) AS patient_day_key,
    patient_key,
    onset_date,
    date_key,
    region_key,
    weather_type_key,
    disease_event_count,
    rainy_day_flag
FROM aggregated
{% if is_incremental() %}
WHERE onset_date > (SELECT MAX(onset_date) FROM {{ this }})
{% endif %}
