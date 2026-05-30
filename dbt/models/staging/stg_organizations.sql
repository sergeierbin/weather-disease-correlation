SELECT
    id   AS organization_id,
    city,
    state,
    lat,
    lon
FROM {{ source('raw', 'organizations') }}
