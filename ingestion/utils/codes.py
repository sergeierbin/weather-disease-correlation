import csv
from pathlib import Path

_CSV_PATH = Path(__file__).parent.parent / "icd_snomed.csv"


def _load():
    icd_codes    = []
    snomed_codes = set()

    with open(_CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            icd_codes.append(row["icd10_code"])
            snomed_codes.add(row["snomed_code"])

    return icd_codes, snomed_codes


TARGET_ICD_CODES, TARGET_SNOMED_CODES = _load()
