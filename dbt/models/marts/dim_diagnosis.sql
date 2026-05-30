SELECT
    ROW_NUMBER() OVER (ORDER BY icd10_code) AS diagnosis_key,
    icd10_code,
    snomed_code AS condition_code_snomed,
    description_et AS diagnosis_name
FROM {{ ref('stg_icd_codes') }}
