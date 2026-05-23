-- Staging model for healthcare organisations (hospitals, clinics).
-- Changes from raw:
--   - loaded_at removed (internal ingestion metadata)

WITH source AS (
    SELECT * FROM {{ source('raw', 'organizations') }}
),

renamed AS (
    SELECT
        id              AS organization_id,
        name,
        city,
        state,
        type_code,
        type_display
    FROM source
)

SELECT * FROM renamed
