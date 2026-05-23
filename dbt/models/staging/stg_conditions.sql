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
        abatement_datetime
    FROM source
)

SELECT * FROM renamed
