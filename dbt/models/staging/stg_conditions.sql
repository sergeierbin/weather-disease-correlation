WITH source AS (
    SELECT * FROM {{ source('raw', 'conditions') }}
),

renamed AS (
    SELECT
        condition_id,
        patient_id,
        encounter_id,
        condition_code,
        condition_display,
        clinical_status,
        onset_datetime,
        abatement_datetime
    FROM source
)

SELECT * FROM renamed
