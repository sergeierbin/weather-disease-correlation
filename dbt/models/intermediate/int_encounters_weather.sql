-- Intermediate model: encounters joined with weather on the visit date and patient location.
-- One row per encounter — weather columns are NULL if no station data is available.
-- Used by: fct_encounters

WITH encounters AS (
    SELECT * FROM {{ ref('stg_encounters') }}
),

patients AS (
    -- Needed only for lat/lon — the location where the patient lives
    SELECT * FROM {{ ref('stg_patients') }}
),

weather AS (
    SELECT * FROM {{ ref('stg_weather') }}
),

joined AS (
    SELECT
        -- Encounter fields
        e.encounter_id,
        e.patient_id,
        e.period_start,
        e.period_end,
        e.duration_minutes,
        e.class_code,
        e.type_display,
        e.reason_code,
        e.reason_display,

        -- Patient coordinates (rounded to match the precision stored in raw.weather)
        ROUND(p.lat::NUMERIC, 4)  AS lat,
        ROUND(p.lon::NUMERIC, 4)  AS lon,

        -- Weather on the day of the encounter (NULL if no station found nearby)
        w.tavg,   -- average temperature °C
        w.tmin,   -- minimum temperature °C
        w.tmax,   -- maximum temperature °C
        w.prcp,   -- precipitation mm
        w.pres    -- air pressure hPa

    FROM encounters e

    -- Join patients to get lat/lon for the weather lookup
    INNER JOIN patients p ON p.patient_id = e.patient_id

    -- Match weather by rounded coordinates and the encounter date
    -- LEFT JOIN keeps encounters where no weather data exists for that day/location
    LEFT JOIN weather w
        ON  w.lat          = ROUND(p.lat::NUMERIC, 4)
        AND w.lon          = ROUND(p.lon::NUMERIC, 4)
        AND w.weather_date = e.period_start::DATE
)

SELECT * FROM joined
