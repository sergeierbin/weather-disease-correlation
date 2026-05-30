# Loads the ICD-10 / SNOMED mapping from ingestion/icd_snomed.csv into raw.icd10_codes.
# Safe to re-run — existing rows are skipped (ON CONFLICT DO NOTHING).

import os
import sys
import csv
import logging
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_connection, execute_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CSV_PATH = Path(__file__).parent / "icd_snomed.csv"

INSERT_SQL = """
    INSERT INTO raw.icd10_codes (icd10_code, description_et, snomed_code)
    VALUES %s
    ON CONFLICT (icd10_code, snomed_code) DO NOTHING
"""


def load_csv():
    rows = []
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            rows.append((row["icd10_code"], row["description_et"], row["snomed_code"]))
    return rows


def main():
    rows = load_csv()
    log.info("Read %d rows from %s", len(rows), CSV_PATH.name)

    conn = get_connection()
    try:
        execute_values(conn, INSERT_SQL, rows)
        conn.commit()
        log.info("Loaded %d rows into raw.icd10_codes", len(rows))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
