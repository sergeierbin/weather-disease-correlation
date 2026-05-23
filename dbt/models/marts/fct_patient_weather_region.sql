WITH conditions_with_encounter AS (
    SELECT
        c.condition_id,
        c.patient_id,
        c.encounter_id,
        c.condition_code         AS snomed_code,
        c.clinical_status,
        c.onset_datetime::DATE   AS condition_start,
        c.abatement_datetime::DATE AS condition_end,
        e.period_start::DATE     AS encounter_date,
        e.organization_id
    FROM {{ ref('stg_conditions') }} c
    LEFT JOIN {{ ref('stg_encounters') }} e ON e.encounter_id = c.encounter_id
),

with_region AS (
    SELECT
        cwe.*,
        r.region_key
    FROM conditions_with_encounter cwe
    LEFT JOIN {{ ref('stg_organizations') }} o
        ON o.organization_id = cwe.organization_id
    LEFT JOIN {{ ref('dim_region') }} r
        ON r.city_name = o.city AND r.state_name = o.state
),

with_date AS (
    SELECT
        wr.*,
        d.date_key
    FROM with_region wr
    LEFT JOIN {{ ref('dim_date') }} d ON d.full_date = wr.encounter_date
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
        ON w.lat = ol.lat AND w.lon = ol.lon AND w.weather_date = wd.encounter_date
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
            ELSE                     'kõrge'
        END
)

SELECT
    ROW_NUMBER() OVER (ORDER BY patient_id, encounter_date, condition_id) AS patient_weather_key,
    patient_id,
    snomed_code,
    date_key,
    region_key,
    encounter_id,
    condition_start,
    condition_end,
    NULL::BOOLEAN    AS pain_related_flag,  -- definitsioon on lahtine, vt küsimused.md
    prcp > 0         AS rainy_day_flag,
    weather_category_key,
    clinical_status  AS condition_clinical
FROM with_weather
