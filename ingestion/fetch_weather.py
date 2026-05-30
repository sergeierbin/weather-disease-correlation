# Fetches daily weather observations for each unique condition organisation location
# and loads them into raw.weather.
#
# Strategy:
#   1. Query raw.conditions + raw.encounters + raw.organizations (lat/lon stored here)
#      to find each unique (organisation, lat, lon, onset_date) combination.
#   2. Group by (lat, lon) and fetch one date range per location
#      (min(onset_dates)-1 through max(onset_dates)) — avoids N API calls
#      per location when the same site has many condition onset dates.
#   3. Upsert rows into raw.weather (safe to re-run; duplicates are ignored).

import os
import sys
import logging
from collections import defaultdict
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


def fetch_weather(lat, lon, start, end):
    """Fetch all daily weather rows for (lat, lon) between start and end (inclusive)."""
    start_dt = datetime(start.year, start.month, start.day)
    end_dt   = datetime(end.year, end.month, end.day)
    data = Daily(Point(lat, lon), start_dt, end_dt).fetch()
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


def group_dates_by_location(rows_in):
    """Return {(lat, lon): set_of_onset_dates} and {(lat, lon): (city, state)}."""
    loc_dates = defaultdict(set)
    loc_meta  = {}
    for _org_id, city, state, lat, lon, onset_date in rows_in:
        key = (lat, lon)
        loc_dates[key].add(onset_date)
        loc_meta[key] = (city, state)
    return loc_dates, loc_meta


def main():
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute(CONDITION_DATES_SQL, (TODAY,))
        rows_in = cur.fetchall()

    loc_dates, loc_meta = group_dates_by_location(rows_in)
    log.info(
        "Found %d unique (location, date) combos across %d locations",
        len(rows_in), len(loc_dates),
    )

    all_rows = []
    for i, ((lat, lon), dates) in enumerate(loc_dates.items(), 1):
        city, state = loc_meta[(lat, lon)]
        start = min(dates) - timedelta(days=1)
        end   = max(dates)
        log.info(
            "[%d/%d] %s, %s (%.4f, %.4f) %s→%s (%d onset dates)",
            i, len(loc_dates), city, state, lat, lon, start, end, len(dates),
        )
        try:
            rows = fetch_weather(lat, lon, start, end)
        except Exception as exc:
            log.warning("Weather fetch failed for %s, %s: %s", city, state, exc)
            continue
        if not rows:
            log.warning("No weather data for %s, %s", city, state)
            continue
        all_rows.extend(rows)

    if all_rows:
        execute_values(conn, INSERT_SQL, all_rows)
        conn.commit()
    log.info("Done — %d total rows loaded into raw.weather", len(all_rows))
    conn.close()


if __name__ == "__main__":
    main()
