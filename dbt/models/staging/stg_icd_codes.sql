-- Staging model for WHO ICD-10 disease classification codes.
-- Changes from raw:
--   - loaded_at removed (internal ingestion metadata)

WITH source AS (
    SELECT * FROM {{ source('raw', 'icd_codes') }}
),

renamed AS (
    SELECT
        code,
        title,
        description,
        parent_code
    FROM source
)

SELECT * FROM renamed
