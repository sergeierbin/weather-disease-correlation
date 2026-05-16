-- Staging model for healthcare encounters (visits).
-- Changes from raw:
--   - loaded_at removed (internal ingestion metadata)
--   - duration_minutes added (length of visit in minutes)

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

        -- Duration of the visit in minutes; NULL if start or end is missing
        CASE
            WHEN period_start IS NOT NULL AND period_end IS NOT NULL
            THEN ROUND(
                EXTRACT(EPOCH FROM (period_end - period_start)) / 60.0
            )
        END                                             AS duration_minutes

    FROM source
)

SELECT * FROM renamed
