-- Dimension table: one row per unique condition (diagnosis).
-- Grain: condition_id (unique)
-- Used by: fct_encounters (JOIN on condition_id)
-- Note: Synthea uses SNOMED CT codes. The ICD-10 join will mostly return NULLs
-- because a SNOMED-to-ICD-10 mapping table is not yet available.

WITH conditions AS (
    SELECT DISTINCT
        condition_id,
        condition_code,
        condition_code_system,
        condition_display,
        clinical_status,
        verification_status,
        category_code,
        is_chronic
    FROM {{ ref('stg_conditions') }}
),

icd AS (
    SELECT * FROM {{ ref('stg_icd_codes') }}
)

SELECT
    c.condition_id,
    c.condition_code,
    c.condition_code_system,
    c.condition_display,
    c.clinical_status,
    c.verification_status,
    c.category_code,
    c.is_chronic,

    -- ICD-10 enrichment via LEFT JOIN on condition_code
    -- Only populates when condition_code matches an ICD-10 code (rare with SNOMED data)
    i.title        AS icd_title,
    i.description  AS icd_description,
    i.parent_code  AS icd_parent_code

FROM conditions c
LEFT JOIN icd i ON i.code = c.condition_code
