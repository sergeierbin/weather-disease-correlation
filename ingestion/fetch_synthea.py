# Parses Synthea FHIR R4 JSON bundles and loads five resource types into PostgreSQL:
#   Patient      → raw.patients
#   Encounter    → raw.encounters
#   Organization → raw.organizations
#   Condition    → raw.conditions
#   Location     → raw.organization_locations (lat/lon coordinates per organization)
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
from utils.codes import TARGET_SNOMED_CODES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Directory containing Synthea FHIR bundles — override with FHIR_DIR env var
FHIR_DIR = Path(os.environ.get("FHIR_DIR", "/opt/airflow/synthea_output/fhir"))

# Max number of patient files to process — 0 means no limit (override with FHIR_LIMIT env var)
FHIR_LIMIT = int(os.environ.get("FHIR_LIMIT", "0"))


# ── FHIR helpers ──────────────────────────────────────────────────────────────

def strip_urn(reference):
    if not reference:
        return None
    # Standard FHIR URN: "urn:uuid:abc-123"
    if reference.startswith("urn:uuid:"):
        return reference[len("urn:uuid:"):]
    # Synthea conditional reference: "Organization?identifier=...synthea|<uuid>"
    if "|" in reference:
        return reference.split("|")[-1]
    return reference


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
        strip_urn(r.get("serviceProvider", {}).get("reference")),  # organization_id FK
    )


def parse_organization(r):
    address  = first(r.get("address", []), {})
    org_type = first(r.get("type", []), {})

    return (
        r["id"],
        r.get("name"),
        address.get("city"),
        address.get("state"),
        coding_value(org_type, "code"),
        coding_value(org_type, "display"),
    )


def parse_location(r):
    position = r.get("position", {})
    org_ref  = r.get("managingOrganization", {}).get("identifier", {}).get("value")
    lat = position.get("latitude")
    lon = position.get("longitude")
    if org_ref is None or lat is None or lon is None:
        return None
    return (org_ref, round(lat, 6), round(lon, 6))


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

    patients      = []
    encounters    = []
    organizations = []
    conditions    = []
    locations     = []

    for entry in bundle.get("entry", []):
        r     = entry.get("resource", {})
        rtype = r.get("resourceType")  # Identifies the type of clinical data

        # Route each resource to the correct parser — ignore other types (Claim, etc.)
        if rtype == "Patient":
            patients.append(parse_patient(r))
        elif rtype == "Encounter":
            row = parse_encounter(r)
            reason_code = row[11]  # reason_code is the 12th field in parse_encounter
            if reason_code in TARGET_SNOMED_CODES:
                encounters.append(row)
        elif rtype == "Organization":
            organizations.append(parse_organization(r))
        elif rtype == "Condition":
            row = parse_condition(r)
            condition_code = row[6]  # condition_code is the 7th field in parse_condition
            if condition_code in TARGET_SNOMED_CODES:
                conditions.append(row)
        elif rtype == "Location":
            row = parse_location(r)
            if row is not None:
                locations.append(row)

    return patients, encounters, organizations, conditions, locations

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
         location_display, service_provider_display, reason_code, reason_display,
         organization_id)
    VALUES %s
    ON CONFLICT (encounter_id) DO NOTHING
"""

ORGANIZATIONS_SQL = """
    INSERT INTO raw.organizations
        (id, name, city, state, type_code, type_display)
    VALUES %s
    ON CONFLICT (id) DO NOTHING
"""

ORG_LOCATIONS_SQL = """
    INSERT INTO raw.organization_locations (organization_id, lat, lon)
    VALUES %s
    ON CONFLICT (organization_id) DO NOTHING
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

    all_patients      = []
    all_encounters    = []
    all_organizations = []
    all_conditions    = []
    all_locations     = []

    patient_count = 0
    for path in files:
        try:
            if path.stem.startswith("hospitalInformation"):
                # Hospital bundles contain Organization and Location resources
                _, _, o, _, l = parse_bundle(path)
                all_organizations.extend(o)
                all_locations.extend(l)
            elif path.stem.startswith("practitionerInformation"):
                continue
            else:
                if FHIR_LIMIT and patient_count >= FHIR_LIMIT:
                    continue
                p, e, o, c, _ = parse_bundle(path)
                all_patients.extend(p)
                all_encounters.extend(e)
                all_organizations.extend(o)
                all_conditions.extend(c)
                patient_count += 1
        except Exception as exc:
            log.warning("Skipping %s: %s", path.name, exc)

    # Null out encounter_id on conditions that reference filtered-out encounters
    kept_encounter_ids = {e[0] for e in all_encounters}
    all_conditions = [
        (c[0], c[1], c[2] if c[2] in kept_encounter_ids else None, *c[3:])
        for c in all_conditions
    ]

    # Keep only organizations linked to a relevant encounter
    kept_org_ids = {e[13] for e in all_encounters if e[13] is not None}
    all_organizations = [o for o in all_organizations if o[0] in kept_org_ids]
    all_locations     = [l for l in all_locations     if l[0] in kept_org_ids]

    log.info(
        "Parsed %d patients, %d encounters, %d organizations, %d conditions, %d locations",
        len(all_patients), len(all_encounters), len(all_organizations), len(all_conditions), len(all_locations),
    )

    conn = get_connection()
    try:
        # Insert in FK dependency order: patients and organizations first, then encounters, then conditions
        execute_values(conn, PATIENTS_SQL,      all_patients)
        log.info("Loaded %d rows → raw.patients", len(all_patients))

        execute_values(conn, ORGANIZATIONS_SQL, all_organizations)
        log.info("Loaded %d rows → raw.organizations", len(all_organizations))

        execute_values(conn, ENCOUNTERS_SQL,    all_encounters)
        log.info("Loaded %d rows → raw.encounters", len(all_encounters))

        execute_values(conn, CONDITIONS_SQL,    all_conditions)
        log.info("Loaded %d rows → raw.conditions", len(all_conditions))

        execute_values(conn, ORG_LOCATIONS_SQL, all_locations)
        log.info("Loaded %d rows → raw.organization_locations", len(all_locations))
    finally:
        conn.close()  # Always close, even if an insert raises

if __name__ == "__main__":
    main()
