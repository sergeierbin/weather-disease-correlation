# Parses Synthea FHIR R4 JSON bundles and loads three resource types into PostgreSQL:
#   Patient   → raw.patients
#   Encounter → raw.encounters
#   Condition → raw.conditions
#
# Input:  FHIR_DIR (env var or default ./synthea/output/fhir) — one JSON file per patient
# Output: upserted rows in the raw schema (safe to re-run; duplicates are skipped)

import os
import sys
import json
import logging
from pathlib import Path

# Allow imports from the ingestion/ package root (e.g. utils.db)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_connection, execute_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Directory containing Synthea FHIR bundles — override with FHIR_DIR env var
FHIR_DIR = Path(os.environ.get("FHIR_DIR", "/opt/airflow/synthea_output/fhir"))

# ── FHIR helpers ──────────────────────────────────────────────────────────────

def strip_urn(reference):
    # FHIR cross-references are formatted as "urn:uuid:abc-123" — strip the prefix
    # to get a plain UUID that matches the id field in the target table
    if not reference:
        return None
    return reference.replace("urn:uuid:", "")


def first(lst, default=None):
    # Many FHIR fields are arrays but Synthea always puts the primary value first
    if lst:
        return lst[0]
    return default


def coding_value(obj, field, default=None):
    # FHIR CodeableConcept: {"coding": [{"code": "...", "display": "..."}]}
    # Returns the requested field from the first coding entry, or default if missing
    try:
        return obj["coding"][0][field]
    except (TypeError, KeyError, IndexError):
        return default

# ── Resource parsers ──────────────────────────────────────────────────────────

def parse_patient(r):
    address = first(r.get("address", []), {})

    lat = lon = None
    # Lat/lon are three levels deep: address → extension (geolocation) → extension[]
    for ext in address.get("extension", []):
        if "geolocation" in ext.get("url", ""):
            for geo in ext.get("extension", []):
                if geo.get("url") == "latitude":
                    lat = geo.get("valueDecimal")
                elif geo.get("url") == "longitude":
                    lon = geo.get("valueDecimal")
            break  # Only one geolocation block per address

    return (
        r["id"],
        r.get("birthDate"),          # "YYYY-MM-DD" string — psycopg2 converts to DATE
        r.get("gender"),             # "male" or "female"
        address.get("city"),
        address.get("state"),        # Two-letter state code, e.g. "MA"
        lat,
        lon,                         # Used by fetch_weather.py for location-based lookup
        r.get("deceasedDateTime"),   # None if patient is still alive
    )


def parse_encounter(r):
    participant = first(r.get("participant", []), {})  # Primary care provider
    location    = first(r.get("location", []), {})     # Where the visit took place
    reason      = first(r.get("reasonCode", []), {})   # Why the patient came in
    enc_type    = first(r.get("type", []), {})          # Visit type (e.g. office visit)
    period      = r.get("period", {})                  # Start and end timestamps

    return (
        r["id"],                                              # encounter_id
        r.get("status"),                                      # e.g. "finished"
        r.get("class", {}).get("code"),                       # e.g. "AMB" (ambulatory)
        coding_value(enc_type, "code"),                       # SNOMED procedure code
        coding_value(enc_type, "display"),                    # Human-readable type
        strip_urn(r.get("subject", {}).get("reference")),     # patient_id FK
        period.get("start"),                                  # ISO 8601 timestamp
        period.get("end"),
        participant.get("individual", {}).get("display"),     # Practitioner full name
        location.get("location", {}).get("display"),          # Clinic or hospital name
        r.get("serviceProvider", {}).get("display"),          # Organisation name
        coding_value(reason, "code"),                         # SNOMED reason code
        coding_value(reason, "display"),                      # Human-readable reason
    )


def parse_condition(r):
    code_obj = r.get("code", {})  # The diagnosis CodeableConcept

    return (
        r["id"],                                                       # condition_id
        strip_urn(r.get("subject", {}).get("reference")),              # patient_id FK
        strip_urn(r.get("encounter", {}).get("reference")),            # encounter_id FK (nullable)
        coding_value(r.get("clinicalStatus", {}), "code"),             # e.g. "active", "resolved"
        coding_value(r.get("verificationStatus", {}), "code"),         # e.g. "confirmed"
        coding_value(first(r.get("category", []), {}), "code"),        # e.g. "encounter-diagnosis"
        coding_value(code_obj, "code"),                                # SNOMED code
        coding_value(code_obj, "system"),                              # Coding system URI
        coding_value(code_obj, "display"),                             # Human-readable name
        r.get("onsetDateTime"),                                        # When condition started
        r.get("recordedDate"),                                         # When it was documented
        r.get("abatementDateTime"),                                    # None if condition ongoing
    )

# ── Bundle reader ─────────────────────────────────────────────────────────────

def parse_bundle(path):
    # Each FHIR bundle file contains all resources for one patient in a flat entry list
    with open(path, encoding="utf-8") as f:
        bundle = json.load(f)

    patients   = []
    encounters = []
    conditions = []

    for entry in bundle.get("entry", []):
        r     = entry.get("resource", {})
        rtype = r.get("resourceType")  # Identifies the type of clinical data

        # Route each resource to the correct parser — ignore other types (Claim, etc.)
        if rtype == "Patient":
            patients.append(parse_patient(r))
        elif rtype == "Encounter":
            encounters.append(parse_encounter(r))
        elif rtype == "Condition":
            conditions.append(parse_condition(r))

    return patients, encounters, conditions

# ── SQL statements ────────────────────────────────────────────────────────────

# ON CONFLICT DO NOTHING — re-running the script is safe; existing rows are kept as-is
PATIENTS_SQL = """
    INSERT INTO raw.patients
        (id, birthdate, gender, city, state, lat, lon, deceased_datetime)
    VALUES %s
    ON CONFLICT (id) DO NOTHING
"""

ENCOUNTERS_SQL = """
    INSERT INTO raw.encounters
        (encounter_id, status, class_code, type_code, type_display,
         patient_id, period_start, period_end, practitioner_display,
         location_display, service_provider_display, reason_code, reason_display)
    VALUES %s
    ON CONFLICT (encounter_id) DO NOTHING
"""

CONDITIONS_SQL = """
    INSERT INTO raw.conditions
        (condition_id, patient_id, encounter_id, clinical_status,
         verification_status, category_code, condition_code, condition_code_system,
         condition_display, onset_datetime, recorded_date, abatement_datetime)
    VALUES %s
    ON CONFLICT (condition_id) DO NOTHING
"""

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    files = sorted(FHIR_DIR.glob("*.json"))
    if not files:
        log.error("No FHIR JSON files found in %s", FHIR_DIR)
        return

    log.info("Found %d FHIR bundle files in %s", len(files), FHIR_DIR)

    all_patients   = []
    all_encounters = []
    all_conditions = []

    for path in files:
        # Skip hospital and practitioner info bundles — they contain no Patient resources
        if path.stem.startswith(("hospitalInformation", "practitionerInformation")):
            continue
        try:
            p, e, c = parse_bundle(path)
            all_patients.extend(p)
            all_encounters.extend(e)
            all_conditions.extend(c)
        except Exception as exc:
            log.warning("Skipping %s: %s", path.name, exc)

    log.info(
        "Parsed %d patients, %d encounters, %d conditions",
        len(all_patients), len(all_encounters), len(all_conditions),
    )

    conn = get_connection()
    try:
        # Insert in FK dependency order: patients first, then encounters, then conditions
        execute_values(conn, PATIENTS_SQL,   all_patients)
        log.info("Loaded %d rows → raw.patients", len(all_patients))

        execute_values(conn, ENCOUNTERS_SQL, all_encounters)
        log.info("Loaded %d rows → raw.encounters", len(all_encounters))

        execute_values(conn, CONDITIONS_SQL, all_conditions)
        log.info("Loaded %d rows → raw.conditions", len(all_conditions))
    finally:
        conn.close()  # Always close, even if an insert raises

if __name__ == "__main__":
    main()
