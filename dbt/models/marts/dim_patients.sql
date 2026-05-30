SELECT
    MD5(patient_id) AS patient_key,
    patient_id AS source_patient_id,
    state
FROM {{ ref('stg_patients') }}
