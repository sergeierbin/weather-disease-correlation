WITH conditions_with_encounter AS (
    SELECT
        c.condition_id,
        c.patient_id,
        c.encounter_id,
        c.condition_code         AS snomed_code,
        c.clinical_status,
        c.onset_datetime::DATE   AS condition_start,
        c.abatement_datetime::DATE AS condition_end,
        e.organization_id
    FROM {{ ref('stg_conditions') }} c
    LEFT JOIN {{ ref('stg_encounters') }} e ON e.encounter_id = c.encounter_id
),

with_region AS (
    SELECT
        cwe.*,
        r.region_key,
        p.state AS patient_state
    FROM conditions_with_encounter cwe
    LEFT JOIN {{ ref('stg_organizations') }} o
        ON o.organization_id = cwe.organization_id
    LEFT JOIN {{ ref('dim_region') }} r
        ON r.city_name = o.city AND r.state_name = o.state
    LEFT JOIN {{ ref('dim_patients') }} p
        ON p.patient_id = cwe.patient_id
),

with_date AS (
    SELECT
        wr.*,
        d.date_key
    FROM with_region wr
    LEFT JOIN {{ ref('dim_date') }} d ON d.full_date = wr.condition_start
),

with_weather AS (
    SELECT
        wd.*,
        w.prcp,
        wc.weather_category_key
    FROM with_date wd
    LEFT JOIN {{ ref('stg_organization_locations') }} ol
        ON ol.organization_id = wd.organization_id
    LEFT JOIN {{ ref('stg_weather') }} w
        ON w.lat = ol.lat AND w.lon = ol.lon AND w.weather_date = wd.condition_start
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
    ROW_NUMBER() OVER (ORDER BY patient_id, condition_start, condition_id) AS patient_weather_key,
    patient_id,
    patient_state,
    snomed_code,
    clinical_status,
    date_key,
    region_key,
    encounter_id,
    condition_start,
    condition_end,
    TRUE             AS pain_related_flag,
    prcp > 0         AS rainy_day_flag,
    weather_category_key
FROM with_weather
