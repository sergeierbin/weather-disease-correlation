WITH regions AS (
    SELECT DISTINCT
        o.city   AS city_name,
        o.state  AS state_name,
        ol.lat   AS latitude,
        ol.lon   AS longitude
    FROM {{ ref('stg_organizations') }} o
    JOIN {{ ref('stg_organization_locations') }} ol
        ON ol.organization_id = o.organization_id
)

SELECT
    ROW_NUMBER() OVER (ORDER BY state_name, city_name) AS region_key,
    city_name,
    state_name,
    latitude,
    longitude
FROM regions
