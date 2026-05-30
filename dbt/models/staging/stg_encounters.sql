WITH source AS (
    SELECT * FROM {{ source('raw', 'encounters') }}
),

renamed AS (
    SELECT
        encounter_id,
        patient_id,
        organization_id,
        reason_code,
        reason_display
    FROM source
)

SELECT * FROM renamed
