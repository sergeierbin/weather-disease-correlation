# Fetches daily weather observations for each unique patient location and loads
# them into raw.weather via the Meteostat Python library.
#
# Strategy:
#   1. Query raw.patients + raw.encounters to find each unique (lat, lon) and
#      the full date range covered by that patient's encounters.
#   2. Round coordinates to 4 decimal places (~11 m) before lookup — Meteostat
#      resolves to the nearest weather station, so fine-grained differences
#      don't affect the result but do affect the UNIQUE key in raw.weather.
#   3. Fetch daily weather from Meteostat for each location + date range.
#   4. Upsert rows into raw.weather (safe to re-run; duplicates are ignored).
#
# Package versions: meteostat==1.6.8 requires numpy==1.26.4 + pandas==2.1.4.
# Newer pandas breaks meteostat's internal parse_dates usage.

import os
import sys
import logging
from datetime import datetime

import pandas as pd
from meteostat import Point, Daily  # Point = location, Daily = daily observations

# Allow imports from the ingestion/ package root (e.g. utils.db)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_connection, execute_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Clamp the end date to today — Meteostat raises an error for future dates
TODAY = datetime.utcnow().date()

# ── Database queries ──────────────────────────────────────────────────────────

# Group by rounded coordinates so that patients living metres apart share a
# single weather fetch (Meteostat resolves both to the same station anyway).
# LEAST(..., %s) prevents requesting data beyond today's date.
LOCATIONS_SQL = """
    SELECT
        ROUND(p.lat::NUMERIC, 4)            AS lat,
        ROUND(p.lon::NUMERIC, 4)            AS lon,
        MIN(e.period_start)::DATE           AS date_from,
        LEAST(MAX(e.period_end)::DATE, %s)  AS date_to
    FROM raw.patients  p
    JOIN raw.encounters e ON e.patient_id = p.id
    WHERE p.lat IS NOT NULL
      AND p.lon IS NOT NULL
    GROUP BY ROUND(p.lat::NUMERIC, 4), ROUND(p.lon::NUMERIC, 4)
"""

# ON CONFLICT DO NOTHING — safe to re-run; existing rows are left unchanged
INSERT_SQL = """
    INSERT INTO raw.weather (lat, lon, date, tavg, tmin, tmax, prcp, pres)
    VALUES %s
    ON CONFLICT (lat, lon, date) DO NOTHING
"""

# ── Weather fetch ─────────────────────────────────────────────────────────────

def fetch_weather_for_location(lat, lon, date_from, date_to):
    """
    Fetch daily weather from Meteostat for one (lat, lon) over a date range.
    Returns a list of row tuples ready for INSERT, skipping days with no data.
    """
    # Point finds the nearest weather station to the given coordinates
    location = Point(float(lat), float(lon))

    # Meteostat requires datetime objects, not date objects
    start = datetime(date_from.year, date_from.month, date_from.day)
    end   = datetime(date_to.year,   date_to.month,   date_to.day)

    data = Daily(location, start, end).fetch()  # Returns a pandas DataFrame

    if data.empty:
        return []  # No station found near this location

    rows = []
    for date, row in data.iterrows():
        # Skip days where all key measurements are missing (station outage, etc.)
        if pd.isna(row.get("tavg")) and pd.isna(row.get("prcp")) and pd.isna(row.get("pres")):
            continue

        # Convert NaN → None so psycopg2 writes NULL instead of raising a type error
        rows.append((
            float(lat),
            float(lon),
            date.date(),                                      # pandas Timestamp → Python date
            None if pd.isna(row.get("tavg")) else float(row["tavg"]),  # avg temperature °C
            None if pd.isna(row.get("tmin")) else float(row["tmin"]),  # min temperature °C
            None if pd.isna(row.get("tmax")) else float(row["tmax"]),  # max temperature °C
            None if pd.isna(row.get("prcp")) else float(row["prcp"]),  # precipitation mm
            None if pd.isna(row.get("pres")) else float(row["pres"]),  # air pressure hPa
        ))

    return rows

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    conn = get_connection()

    # Step 1: get unique locations and their encounter date ranges from the DB
    with conn.cursor() as cur:
        cur.execute(LOCATIONS_SQL, (TODAY,))  # Pass today as the upper date cap
        locations = cur.fetchall()

    log.info("Found %d unique patient locations to fetch weather for", len(locations))

    total_rows = 0

    for i, (lat, lon, date_from, date_to) in enumerate(locations, 1):
        log.info(
            "[%d/%d] Fetching weather for (%.4f, %.4f) %s → %s",
            i, len(locations), lat, lon, date_from, date_to,
        )

        try:
            rows = fetch_weather_for_location(lat, lon, date_from, date_to)
        except Exception as exc:
            # Log and continue — one bad location should not abort the whole run
            log.warning("Skipping (%.4f, %.4f): %s", lat, lon, exc)
            continue

        if not rows:
            log.warning("No weather data returned for (%.4f, %.4f)", lat, lon)
            continue

        # Upsert per location to avoid holding all data in memory at once
        execute_values(conn, INSERT_SQL, rows)
        total_rows += len(rows)
        log.info("  → inserted %d daily rows", len(rows))

    log.info("Done — %d total rows loaded into raw.weather", total_rows)
    conn.close()

if __name__ == "__main__":
    main()
