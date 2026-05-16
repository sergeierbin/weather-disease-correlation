-- Dimension table: one row per patient.
-- Grain: patient_id (unique)
-- Used by: fct_encounters (JOIN on patient_id)

WITH source AS (
    SELECT * FROM {{ ref('stg_patients') }}
)

SELECT
    patient_id,
    gender,
    birthdate,

    -- Age calculated from today, not from deceased_datetime, so living patients
    -- always reflect their current age; use age_at_death for deceased patients.
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, birthdate))::INT  AS current_age,

    -- Home city and state for regional grouping in dashboards
    city,
    state,

    -- Home coordinates kept here so fct_encounters can join weather data
    -- via (lat, lon, encounter_date) without going back to the patients table
    lat,
    lon,

    is_deceased,
    deceased_datetime,
    age_at_death  -- NULL for living patients; populated in stg_patients

FROM source
