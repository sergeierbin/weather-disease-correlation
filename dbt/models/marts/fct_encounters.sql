-- Central fact table for the star schema.
-- Grain: one row per (encounter × condition diagnosed at that encounter).
-- An encounter with 3 conditions produces 3 rows.
-- An encounter with no linked conditions produces 1 row with NULL condition fields.
--
-- Answers:
--   - Chronic pain patients by region            (filter is_chronic + condition_display)
--   - Rainy days + chronic diagnoses by region   (filter prcp + is_chronic)
--   - Rainy day percentage by region             (aggregate prcp)
--   - Most common diagnoses by region            (group by condition_display + city/state)
--   - Weather-disease correlation                (correlate tavg/prcp/pres with condition)

WITH encounters AS (
    SELECT * FROM {{ ref('int_encounters_weather') }}
),

conditions AS (
    SELECT * FROM {{ ref('stg_conditions') }}
)

SELECT
    -- Keys
    e.encounter_id,
    e.patient_id,
    e.period_start::DATE                  AS encounter_date,  -- FK → dim_dates
    c.condition_id,                                           -- FK → dim_conditions (nullable)

    -- Visit attributes (degenerate dimensions — low cardinality, no separate dim needed)
    e.class_code,
    e.type_display,
    e.reason_code,
    e.reason_display,

    -- Location (used to join dim_weather or group by region via dim_patients)
    e.lat,
    e.lon,

    -- Visit metric
    e.duration_minutes,

    -- Weather metrics on the day of the encounter
    e.tavg,
    e.tmin,
    e.tmax,
    e.prcp,
    e.pres,

    -- Condition attributes (denormalised here for correlation queries without extra JOINs)
    c.condition_code,
    c.condition_display,
    c.is_chronic,
    c.clinical_status,
    c.onset_datetime,
    c.abatement_datetime

FROM encounters e
-- Join conditions that were diagnosed during this specific encounter
LEFT JOIN conditions c
    ON  c.patient_id   = e.patient_id
    AND c.encounter_id = e.encounter_id
