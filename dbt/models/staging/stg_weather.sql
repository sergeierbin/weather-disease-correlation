WITH source AS (
    SELECT * FROM {{ source('raw', 'weather') }}
),

renamed AS (
    SELECT
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
