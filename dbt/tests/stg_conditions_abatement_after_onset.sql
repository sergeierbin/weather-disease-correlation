-- Haiguse lõppkuupäev ei saa olla varasem kui alguskuupäev.
SELECT *
FROM {{ ref('stg_conditions') }}
WHERE abatement_datetime < onset_datetime
