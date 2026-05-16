-- Intermediate model: patients joined with their conditions.
-- One row per (patient, condition) pair.
-- Patients with no conditions appear once with NULL condition fields (LEFT JOIN).
-- Used by: dim_patients, dim_conditions, fct_encounters

WITH patients AS (
    SELECT * FROM {{ ref('stg_patients') }}
),

conditions AS (
    SELECT * FROM {{ ref('stg_conditions') }}
),

joined AS (
    SELECT
        -- Patient fields
        p.patient_id,
        p.gender,
        p.birthdate,
        p.city,
        p.state,
        p.lat,
        p.lon,
        p.is_deceased,

        -- Condition fields (NULL for patients with no recorded conditions)
        c.condition_id,
        c.encounter_id,
        c.condition_code,
        c.condition_code_system,
        c.condition_display,
        c.clinical_status,
        c.verification_status,
        c.category_code,
        c.onset_datetime,
        c.recorded_date,
        c.abatement_datetime,
        c.is_chronic

    FROM patients p
    -- LEFT JOIN preserves patients who have no conditions recorded yet
    LEFT JOIN conditions c ON c.patient_id = p.patient_id
)

SELECT * FROM joined
