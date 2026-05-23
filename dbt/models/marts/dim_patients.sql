SELECT
    patient_id,
    birthdate,
    gender,
    city,
    state,
    lat,
    lon,
    deceased_datetime,
    is_deceased,
    age_at_death
FROM {{ ref('stg_patients') }}
