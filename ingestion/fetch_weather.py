# Fetches daily weather observations for each unique condition organisation location
# and loads them into raw.weather.
#
# Strategy:
#   1. Query raw.conditions + raw.encounters + raw.organizations + raw.organization_locations
#      to find each unique (organisation, lat, lon, onset_date) combination.
#   2. For each onset date, fetch weather for that day AND the previous day.
#   3. Fetch daily historical weather from Meteostat for each location and date.
#   4. Upsert rows into raw.weather (safe to re-run; duplicates are ignored).
#
# Coordinates come directly from raw.organization_locations, which is populated by
# fetch_synthea.py from the Location resources in the hospitalInformation FHIR bundles.

import os
import sys
import logging
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_connection, execute_values

from meteostat import Point, Daily

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TODAY = date.today()

CONDITION_DATES_SQL = """
    SELECT DISTINCT
        o.id,
        o.city,
        o.state,
        o.lat,
        o.lon,
        c.onset_datetime::DATE AS onset_date
    FROM raw.conditions c
    JOIN raw.encounters e ON e.encounter_id = c.encounter_id
    JOIN raw.organizations o ON o.id = e.organization_id
    WHERE c.onset_datetime IS NOT NULL
      AND c.onset_datetime::DATE <= %s
      AND o.lat IS NOT NULL
    ORDER BY o.id, c.onset_datetime::DATE
"""

INSERT_SQL = """
    INSERT INTO raw.weather (lat, lon, date, tavg, tmin, tmax, prcp, pres)
    VALUES %s
    ON CONFLICT (lat, lon, date) DO NOTHING
"""


def fetch_weather(lat, lon, target_date):
    prev_date = target_date - timedelta(days=1)
    start_dt = datetime(prev_date.year, prev_date.month, prev_date.day)
    end_dt   = datetime(target_date.year, target_date.month, target_date.day)
    point = Point(lat, lon)
    data = Daily(point, start_dt, end_dt).fetch()
    if data.empty:
        return []
    rows = []
    for ts, row in data.iterrows():
        row_date = ts.date() if hasattr(ts, "date") else ts
        rows.append((
            lat, lon, row_date,
            row.get("tavg"), row.get("tmin"), row.get("tmax"),
            row.get("prcp"), row.get("pres"),
        ))
    return rows


def main():
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute(CONDITION_DATES_SQL, (TODAY,))
        rows_in = cur.fetchall()

    log.info("Found %d unique condition onset dates to fetch weather for", len(rows_in))

    total_rows = 0

    for i, (org_id, city, state, lat, lon, onset_date) in enumerate(rows_in, 1):
        log.info("[%d/%d] %s, %s (%.4f, %.4f) on %s (+ prev day)", i, len(rows_in), city, state, lat, lon, onset_date)

        try:
            rows = fetch_weather(lat, lon, onset_date)
        except Exception as exc:
            log.warning("Weather fetch failed for %s, %s on %s: %s", city, state, onset_date, exc)
            continue

        if not rows:
            log.warning("No weather data for %s, %s on %s", city, state, onset_date)
            continue

        execute_values(conn, INSERT_SQL, rows)
        total_rows += len(rows)

    log.info("Done — %d total rows loaded into raw.weather", total_rows)
    conn.close()


if __name__ == "__main__":
    main()
