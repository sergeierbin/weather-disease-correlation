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

# Number of patient files to accumulate before each DB insert (override with FHIR_BATCH_SIZE env var)
FHIR_BATCH_SIZE = int(os.environ.get("FHIR_BATCH_SIZE", "100"))


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
    return (
        r["id"],
        address.get("state"),  # Two-letter state code, e.g. "MA"
    )


def parse_encounter(r):
    reason = first(r.get("reasonCode", []), {})
    return (
        r["id"],                                                   # encounter_id
        strip_urn(r.get("subject", {}).get("reference")),          # patient_id FK
        coding_value(reason, "code"),                              # SNOMED reason code
        coding_value(reason, "display"),                           # Human-readable reason
        strip_urn(r.get("serviceProvider", {}).get("reference")),  # organization_id FK
    )


def parse_organization(r):
    address = first(r.get("address", []), {})
    return (
        r["id"],
        address.get("city"),
        address.get("state"),
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
    code_obj = r.get("code", {})
    return (
        r["id"],                                                       # condition_id
        strip_urn(r.get("subject", {}).get("reference")),              # patient_id FK
        strip_urn(r.get("encounter", {}).get("reference")),            # encounter_id FK (nullable)
        coding_value(r.get("clinicalStatus", {}), "code"),             # e.g. "active", "resolved"
        coding_value(first(r.get("category", []), {}), "code"),        # e.g. "encounter-diagnosis"
        coding_value(code_obj, "code"),                                # SNOMED code
        coding_value(code_obj, "system"),                              # Coding system URI
        coding_value(code_obj, "display"),                             # Human-readable name
        r.get("onsetDateTime"),                                        # When condition started
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
    location_map  = {}  # org_id → (lat, lon) from Location resources

    for entry in bundle.get("entry", []):
        r     = entry.get("resource", {})
        rtype = r.get("resourceType")  # Identifies the type of clinical data

        # Route each resource to the correct parser — ignore other types (Claim, etc.)
        if rtype == "Patient":
            patients.append(parse_patient(r))
        elif rtype == "Encounter":
            row = parse_encounter(r)
            if row[2] in TARGET_SNOMED_CODES:  # reason_code
                encounters.append(row)
        elif rtype == "Organization":
            organizations.append(parse_organization(r))
        elif rtype == "Condition":
            row = parse_condition(r)
            if row[5] in TARGET_SNOMED_CODES:  # condition_code
                conditions.append(row)
        elif rtype == "Location":
            row = parse_location(r)
            if row is not None:
                location_map[row[0]] = (row[1], row[2])

    # Merge lat/lon from Location resources into each Organization row
    organizations = [
        (o[0], o[1], o[2], *location_map.get(o[0], (None, None)))
        for o in organizations
    ]

    return patients, encounters, organizations, conditions

# ── SQL statements ────────────────────────────────────────────────────────────

# ON CONFLICT DO NOTHING — re-running the script is safe; existing rows are kept as-is
PATIENTS_SQL = """
    INSERT INTO raw.patients
        (id, state)
    VALUES %s
    ON CONFLICT (id) DO NOTHING
"""

ENCOUNTERS_SQL = """
    INSERT INTO raw.encounters
        (encounter_id, patient_id, reason_code, reason_display, organization_id)
    VALUES %s
    ON CONFLICT (encounter_id) DO NOTHING
"""

ORGANIZATIONS_SQL = """
    INSERT INTO raw.organizations
        (id, city, state, lat, lon)
    VALUES %s
    ON CONFLICT (id) DO NOTHING
"""

CONDITIONS_SQL = """
    INSERT INTO raw.conditions
        (condition_id, patient_id, encounter_id, clinical_status,
         category_code, condition_code, condition_code_system,
         condition_display, onset_datetime, abatement_datetime)
    VALUES %s
    ON CONFLICT (condition_id) DO NOTHING
"""

# ── Batch flusher ─────────────────────────────────────────────────────────────

def flush_batch(conn, patients, encounters, organizations, conditions):
    """Insert one batch in FK dependency order. Returns (n_pat, n_enc, n_org, n_cond)."""
    # Null out encounter_id on conditions that reference filtered-out encounters
    kept_enc_ids = {e[0] for e in encounters}
    conditions = [
        (c[0], c[1], c[2] if c[2] in kept_enc_ids else None, *c[3:])
        for c in conditions
    ]

    # Drop patient-bundle org duplicates not linked to any encounter in this batch;
    # hospital-bundle orgs are already committed before patient batches start.
    kept_org_ids = {e[4] for e in encounters if e[4] is not None}
    organizations = [o for o in organizations if o[0] in kept_org_ids]

    execute_values(conn, PATIENTS_SQL,      patients)
    execute_values(conn, ORGANIZATIONS_SQL, organizations)
    execute_values(conn, ENCOUNTERS_SQL,    encounters)
    execute_values(conn, CONDITIONS_SQL,    conditions)

    return len(patients), len(encounters), len(organizations), len(conditions)

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    files = sorted(FHIR_DIR.glob("*.json"))
    if not files:
        log.error("No FHIR JSON files found in %s", FHIR_DIR)
        return

    log.info("Found %d FHIR bundle files in %s", len(files), FHIR_DIR)

    conn = get_connection()
    try:
        # Pass 1: hospital bundles — insert all org+location rows upfront so FK
        # constraints are satisfied before any patient encounter is committed.
        hospital_orgs = []
        for path in files:
            if not path.stem.startswith("hospitalInformation"):
                continue
            try:
                _, _, o, _ = parse_bundle(path)
                hospital_orgs.extend(o)
            except Exception as exc:
                log.warning("Skipping %s: %s", path.name, exc)
        if hospital_orgs:
            execute_values(conn, ORGANIZATIONS_SQL, hospital_orgs)
            log.info("Loaded %d rows → raw.organizations (hospital bundles)", len(hospital_orgs))

        # Pass 2: patient bundles in batches of FHIR_BATCH_SIZE
        patients, encounters, organizations, conditions = [], [], [], []
        patient_count  = 0
        total_patients = total_encounters = total_organizations = total_conditions = 0

        for path in files:
            if path.stem.startswith("hospitalInformation") or path.stem.startswith("practitionerInformation"):
                continue
            if FHIR_LIMIT and patient_count >= FHIR_LIMIT:
                break
            try:
                p, e, o, c = parse_bundle(path)
                patients.extend(p)
                encounters.extend(e)
                organizations.extend(o)
                conditions.extend(c)
                patient_count += 1
            except Exception as exc:
                log.warning("Skipping %s: %s", path.name, exc)
                continue

            if patient_count % FHIR_BATCH_SIZE == 0:
                np, ne, no, nc = flush_batch(conn, patients, encounters, organizations, conditions)
                log.info("Batch %d/%d flushed — %d patients, %d encounters, %d orgs, %d conditions",
                         patient_count // FHIR_BATCH_SIZE,
                         (len(files) // FHIR_BATCH_SIZE) or 1,
                         np, ne, no, nc)
                total_patients += np; total_encounters += ne
                total_organizations += no; total_conditions += nc
                patients, encounters, organizations, conditions = [], [], [], []

        # Flush the final partial batch
        if patients or encounters or organizations or conditions:
            np, ne, no, nc = flush_batch(conn, patients, encounters, organizations, conditions)
            total_patients += np; total_encounters += ne
            total_organizations += no; total_conditions += nc

        log.info(
            "Done — %d patients, %d encounters, %d organizations, %d conditions",
            total_patients, total_encounters, total_organizations, total_conditions,
        )
    finally:
        conn.close()

if __name__ == "__main__":
    main()
