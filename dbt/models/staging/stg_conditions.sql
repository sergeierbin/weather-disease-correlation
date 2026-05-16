-- Staging model for diagnosed conditions.
-- Changes from raw:
--   - loaded_at removed (internal ingestion metadata)
--   - is_chronic added: True if the condition has no end date (still ongoing)

WITH source AS (
    SELECT * FROM {{ source('raw', 'conditions') }}
),

renamed AS (
    SELECT
        condition_id,
        patient_id,
        encounter_id,
        clinical_status,
        verification_status,
        category_code,
        condition_code,
        condition_code_system,
        condition_display,
        onset_datetime,
        recorded_date,
        abatement_datetime,

        -- A condition is considered chronic if it has never been resolved (no abatement date)
        abatement_datetime IS NULL                      AS is_chronic

    FROM source
)

SELECT * FROM renamed
