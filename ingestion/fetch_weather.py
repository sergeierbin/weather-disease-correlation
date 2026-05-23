# Fetches daily weather observations for each unique encounter organisation location
# and loads them into raw.weather.
#
# Strategy:
#   1. Query raw.encounters + raw.organizations to find each unique organisation
#      and the encounter dates.
#   2. Geocode each organisation's city + state to lat/lon using the Open-Meteo
#      geocoding API; store the result in raw.organization_locations.
#   3. Fetch daily historical weather from Meteostat for each location and date.
#   4. Upsert rows into raw.weather (safe to re-run; duplicates are ignored).

import os
import sys
import logging
import requests
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_connection, execute_values

from meteostat import Point, Daily

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TODAY = date.today()

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

ENCOUNTER_DATES_SQL = """
    SELECT DISTINCT
        o.id,
        o.city,
        o.state,
        e.period_start::DATE AS encounter_date
    FROM raw.encounters e
    JOIN raw.organizations o ON o.id = e.organization_id
    WHERE o.city IS NOT NULL
      AND o.state IS NOT NULL
      AND e.period_start::DATE <= %s
    ORDER BY o.id, e.period_start::DATE
"""

INSERT_ORG_LOCATION_SQL = """
    INSERT INTO raw.organization_locations (organization_id, lat, lon)
    VALUES (%s, %s, %s)
    ON CONFLICT (organization_id) DO NOTHING
"""

INSERT_SQL = """
    INSERT INTO raw.weather (lat, lon, date, tavg, tmin, tmax, prcp, pres)
    VALUES %s
    ON CONFLICT (lat, lon, date) DO NOTHING
"""


def geocode(city, state):
    state_name = STATE_NAMES.get(state, state)
    city_title = city.title()
    resp = requests.get(
        GEOCODE_URL,
        params={"name": city_title, "count": 10, "language": "en", "format": "json"},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        log.warning("Geocoding found no results for %s, %s", city_title, state_name)
        return None, None
    for r in results:
        if r.get("admin1", "").lower() == state_name.lower() and r.get("country_code") == "US":
            return round(r["latitude"], 4), round(r["longitude"], 4)
    for r in results:
        if r.get("country_code") == "US":
            log.warning("No exact state match for %s, %s — using %s, %s", city_title, state_name, r["name"], r.get("admin1"))
            return round(r["latitude"], 4), round(r["longitude"], 4)
    log.warning("Geocoding found no US results for %s, %s", city_title, state_name)
    return None, None


def fetch_weather(lat, lon, encounter_date):
    dt = datetime(encounter_date.year, encounter_date.month, encounter_date.day)
    point = Point(lat, lon)
    data = Daily(point, dt, dt).fetch()
    if data.empty:
        return []
    row = data.iloc[0]
    return [(
        lat, lon, encounter_date,
        row.get("tavg"), row.get("tmin"), row.get("tmax"),
        row.get("prcp"), row.get("pres"),
    )]


def main():
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute(ENCOUNTER_DATES_SQL, (TODAY,))
        rows_in = cur.fetchall()

    log.info("Found %d unique encounter dates to fetch weather for", len(rows_in))

    coords_cache = {}
    total_rows   = 0

    for i, (org_id, city, state, encounter_date) in enumerate(rows_in, 1):
        log.info("[%d/%d] %s, %s on %s", i, len(rows_in), city, state, encounter_date)

        if org_id not in coords_cache:
            lat, lon = geocode(city, state)
            if lat is None:
                coords_cache[org_id] = (None, None)
                continue
            coords_cache[org_id] = (lat, lon)
            with conn.cursor() as cur:
                cur.execute(INSERT_ORG_LOCATION_SQL, (org_id, lat, lon))
            conn.commit()
        else:
            lat, lon = coords_cache[org_id]

        if lat is None:
            continue

        try:
            rows = fetch_weather(lat, lon, encounter_date)
        except Exception as exc:
            log.warning("Weather fetch failed for %s, %s on %s: %s", city, state, encounter_date, exc)
            continue

        if not rows:
            log.warning("No weather data for %s, %s on %s", city, state, encounter_date)
            continue

        execute_values(conn, INSERT_SQL, rows)
        total_rows += len(rows)

    log.info("Done — %d total rows loaded into raw.weather", total_rows)
    conn.close()


if __name__ == "__main__":
    main()
