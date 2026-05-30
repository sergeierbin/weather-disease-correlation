SELECT
    id    AS patient_id,
    state
FROM {{ source('raw', 'patients') }}
