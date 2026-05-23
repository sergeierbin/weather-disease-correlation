WITH source AS (
    SELECT * FROM {{ source('raw', 'organization_locations') }}
),

renamed AS (
    SELECT
        organization_id,
        lat,
        lon
    FROM source
)

SELECT * FROM renamed
