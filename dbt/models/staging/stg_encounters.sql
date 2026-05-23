WITH source AS (
    SELECT * FROM {{ source('raw', 'encounters') }}
),

renamed AS (
    SELECT
        encounter_id,
        patient_id,
        status,
        class_code,
        type_code,
        type_display,
        period_start,
        period_end,
        practitioner_display,
        location_display,
        service_provider_display,
        reason_code,
        reason_display,
        organization_id
    FROM source
)

SELECT * FROM renamed
