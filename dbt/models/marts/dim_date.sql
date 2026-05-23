WITH date_spine AS (
    SELECT GENERATE_SERIES(
        (SELECT MIN(period_start)::DATE FROM {{ ref('stg_encounters') }}),
        CURRENT_DATE,
        INTERVAL '1 day'
    )::DATE AS full_date
)

SELECT
    TO_CHAR(full_date, 'YYYYMMDD')::INT AS date_key,
    full_date,
    EXTRACT(YEAR  FROM full_date)::INT AS year,
    EXTRACT(MONTH FROM full_date)::INT AS month,
    EXTRACT(DAY   FROM full_date)::INT AS day
FROM date_spine
