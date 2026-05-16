-- Staging model for patients.
-- Changes from raw:
--   - id renamed to patient_id for clarity across all models
--   - loaded_at removed (internal ingestion metadata, not needed for analysis)
--   - is_deceased added (boolean flag for quick filtering)
--   - age_at_death added (age in years at time of death, NULL if alive)

WITH source AS (
    SELECT * FROM {{ source('raw', 'patients') }}
),

renamed AS (
    SELECT
        id                                              AS patient_id,
        birthdate,
        gender,
        city,
        state,
        lat,
        lon,
        deceased_datetime,

        -- True if the patient has a recorded death date
        deceased_datetime IS NOT NULL                   AS is_deceased,

        -- Age in full years at time of death; NULL if patient is still alive
        CASE
            WHEN deceased_datetime IS NOT NULL
            THEN DATE_PART('year', AGE(deceased_datetime::DATE, birthdate))
        END                                             AS age_at_death

    FROM source
)

SELECT * FROM renamed
