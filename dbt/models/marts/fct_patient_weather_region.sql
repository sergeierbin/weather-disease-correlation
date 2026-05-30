{{ config(materialized='incremental', unique_key='patient_weather_region_key') }}

WITH conditions_with_encounter AS (
    SELECT
        c.condition_id,
        c.patient_id,
        c.encounter_id,
        c.condition_code               AS snomed_code,
        c.clinical_status              AS occurrence_status,
        c.onset_datetime::DATE         AS onset_datetime,
        c.abatement_datetime::DATE     AS abatement_datetime,
        c.loaded_at,
        e.organization_id
    FROM {{ ref('stg_conditions') }} c
    LEFT JOIN {{ ref('stg_encounters') }} e ON e.encounter_id = c.encounter_id
    {% if is_incremental() %}
    WHERE c.loaded_at > (SELECT MAX(loaded_at) FROM {{ this }})
    {% endif %}
),

with_patient AS (
    SELECT
        cwe.*,
        p.patient_key
    FROM conditions_with_encounter cwe
    LEFT JOIN {{ ref('dim_patients') }} p ON p.source_patient_id = cwe.patient_id
),

with_region AS (
    SELECT
        wp.*,
        r.region_key,
        r.latitude,
        r.longitude
    FROM with_patient wp
    LEFT JOIN {{ ref('dim_region') }} r
        ON r.organization_id = wp.organization_id
),

with_date AS (
    SELECT
        wr.*,
        d.date_key
    FROM with_region wr
    LEFT JOIN {{ ref('dim_date') }} d ON d.full_date = wr.onset_datetime
),

with_weather AS (
    SELECT
        wd.condition_id,
        wd.patient_id,
        wd.encounter_id,
        wd.snomed_code,
        wd.occurrence_status,
        wd.onset_datetime,
        wd.abatement_datetime,
        wd.loaded_at,
        wd.organization_id,
        wd.patient_key,
        wd.region_key,
        wd.date_key,
        wc.weather_type_key
    FROM with_date wd
    LEFT JOIN {{ ref('stg_weather') }} w
        ON w.lat = wd.latitude AND w.lon = wd.longitude AND w.weather_date = wd.onset_datetime
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

with_diagnosis AS (
    SELECT
        ww.*,
        d.diagnosis_key
    FROM with_weather ww
    LEFT JOIN {{ ref('dim_diagnosis') }} d ON d.condition_code_snomed = ww.snomed_code
)

SELECT
    MD5(patient_key::text || '|' || onset_datetime::text || '|' || condition_id::text || '|' || COALESCE(diagnosis_key::text, '')) AS patient_weather_region_key,
    patient_key,
    diagnosis_key,
    date_key,
    region_key,
    weather_type_key,
    condition_id,
    encounter_id,
    onset_datetime,
    abatement_datetime,
    occurrence_status,
    loaded_at
FROM with_diagnosis
