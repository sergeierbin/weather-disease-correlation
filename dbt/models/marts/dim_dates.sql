-- Dimension table: one row per calendar date covering all encounter dates.
-- Grain: date (unique)
-- Used by: fct_encounters (JOIN on weather_date)
-- Enriches dates with year, month, season and weekend flag for easy grouping in Superset.

WITH date_spine AS (
    -- Generate one row per day from the earliest to the latest encounter date
    SELECT
        gs::DATE AS date
    FROM GENERATE_SERIES(
        (SELECT MIN(period_start)::DATE FROM {{ ref('stg_encounters') }}),
        (SELECT MAX(period_end)::DATE   FROM {{ ref('stg_encounters') }}),
        INTERVAL '1 day'
    ) AS gs
)

SELECT
    date,
    EXTRACT(YEAR  FROM date)::INT   AS year,
    EXTRACT(MONTH FROM date)::INT   AS month,
    TO_CHAR(date, 'Month')          AS month_name,
    EXTRACT(QUARTER FROM date)::INT AS quarter,
    TO_CHAR(date, 'Day')            AS day_of_week,
    EXTRACT(DOW FROM date) IN (0,6) AS is_weekend,  -- 0 = Sunday, 6 = Saturday

    -- Meteorological seasons (Northern Hemisphere)
    CASE EXTRACT(MONTH FROM date)
        WHEN 12 THEN 'Winter' WHEN 1 THEN 'Winter' WHEN 2  THEN 'Winter'
        WHEN 3  THEN 'Spring' WHEN 4 THEN 'Spring' WHEN 5  THEN 'Spring'
        WHEN 6  THEN 'Summer' WHEN 7 THEN 'Summer' WHEN 8  THEN 'Summer'
        WHEN 9  THEN 'Autumn' WHEN 10 THEN 'Autumn' WHEN 11 THEN 'Autumn'
    END                             AS season

FROM date_spine
