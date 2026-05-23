SELECT
    icd10_code,
    snomed_code,
    description_et AS diagnosis_name
FROM {{ ref('stg_icd_codes') }}
