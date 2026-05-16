-- Staging model for daily weather observations.
-- Changes from raw:
--   - id renamed to weather_id for consistency
--   - loaded_at removed (internal ingestion metadata)

WITH source AS (
    SELECT * FROM {{ source('raw', 'weather') }}
),

renamed AS (
    SELECT
        id    AS weather_id,
        lat,
        lon,
        date  AS weather_date,
        tavg,
        tmin,
        tmax,
        prcp,
        pres
    FROM source
)

SELECT * FROM renamed
