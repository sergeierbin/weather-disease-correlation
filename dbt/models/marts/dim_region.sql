SELECT
    ROW_NUMBER() OVER (ORDER BY state, city, organization_id) AS region_key,
    organization_id,
    city,
    state,
    lat AS latitude,
    lon AS longitude
FROM {{ ref('stg_organizations') }}
WHERE lat IS NOT NULL AND lon IS NOT NULL
