WITH source AS (
    SELECT * FROM {{ source('raw', 'icd10_codes') }}
),

renamed AS (
    SELECT
        icd10_code,
        description_et,
        snomed_code
    FROM source
)

SELECT * FROM renamed
