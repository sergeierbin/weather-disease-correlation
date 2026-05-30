"""
Tests for fetch_synthea.py — validates pure FHIR parsing functions and batch logic.
No database or file I/O needed.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ingestion"))

# Patch codes loading before importing fetch_synthea
from unittest.mock import patch, MagicMock, call
with patch.dict("sys.modules", {"utils.codes": MagicMock(TARGET_SNOMED_CODES=set(), TARGET_ICD_CODES=[])}):
    import importlib
    import fetch_synthea
    importlib.reload(fetch_synthea)

from fetch_synthea import strip_urn, first, coding_value, parse_patient, parse_encounter, \
    parse_organization, parse_location, parse_condition, flush_batch


class TestStripUrn:
    def test_urn_uuid_prefix(self):
        assert strip_urn("urn:uuid:abc-123") == "abc-123"

    def test_pipe_reference(self):
        assert strip_urn("Organization?identifier=synthea|my-uuid") == "my-uuid"

    def test_plain_string(self):
        assert strip_urn("plain-id") == "plain-id"

    def test_none_returns_none(self):
        assert strip_urn(None) is None

    def test_empty_string(self):
        assert strip_urn("") is None


class TestFirst:
    def test_returns_first_element(self):
        assert first([1, 2, 3]) == 1

    def test_empty_list_returns_default(self):
        assert first([]) is None
        assert first([], "default") == "default"

    def test_none_returns_default(self):
        assert first(None) is None


class TestCodingValue:
    def test_returns_code(self):
        obj = {"coding": [{"code": "123", "display": "Pain"}]}
        assert coding_value(obj, "code") == "123"

    def test_returns_display(self):
        obj = {"coding": [{"code": "123", "display": "Pain"}]}
        assert coding_value(obj, "display") == "Pain"

    def test_missing_field_returns_default(self):
        obj = {"coding": [{"code": "123"}]}
        assert coding_value(obj, "display") is None

    def test_empty_coding_returns_default(self):
        obj = {"coding": []}
        assert coding_value(obj, "code") is None

    def test_none_obj_returns_default(self):
        assert coding_value(None, "code") is None


class TestParsePatient:
    def test_full_patient(self):
        r = {"id": "pat-1", "address": [{"state": "MA"}]}
        assert parse_patient(r) == ("pat-1", "MA")

    def test_no_address(self):
        r = {"id": "pat-2", "address": []}
        patient_id, state = parse_patient(r)
        assert patient_id == "pat-2"
        assert state is None


class TestParseEncounter:
    def test_full_encounter(self):
        r = {
            "id": "enc-1",
            "subject": {"reference": "urn:uuid:pat-1"},
            "reasonCode": [{"coding": [{"code": "1234", "display": "Back pain"}]}],
            "serviceProvider": {"reference": "urn:uuid:org-1"},
        }
        result = parse_encounter(r)
        assert result == ("enc-1", "pat-1", "1234", "Back pain", "org-1")

    def test_missing_reason(self):
        r = {
            "id": "enc-2",
            "subject": {"reference": "urn:uuid:pat-2"},
            "reasonCode": [],
            "serviceProvider": {"reference": "urn:uuid:org-2"},
        }
        enc_id, pat_id, reason_code, reason_display, org_id = parse_encounter(r)
        assert enc_id == "enc-2"
        assert reason_code is None


class TestParseOrganization:
    def test_full_organization(self):
        r = {"id": "org-1", "address": [{"city": "Boston", "state": "MA"}]}
        assert parse_organization(r) == ("org-1", "Boston", "MA")

    def test_no_address(self):
        r = {"id": "org-2", "address": []}
        org_id, city, state = parse_organization(r)
        assert org_id == "org-2"
        assert city is None
        assert state is None


class TestFlushBatch:
    """flush_batch applies FK-safety filters before inserting."""

    def _make_conn(self):
        return MagicMock()

    def test_nulls_condition_encounter_id_when_encounter_filtered_out(self):
        # Condition references enc-999, which is NOT in this batch's encounters
        conditions   = [("cond-1", "pat-1", "enc-999", "active", "dx", "1234", "sys", "Pain", None, None)]
        encounters   = [("enc-1", "pat-1", "1234", "Pain", "org-1")]
        patients     = [("pat-1", "MA")]
        organizations = [("org-1", "Boston", "MA", 42.36, -71.06)]

        conn = self._make_conn()
        with patch("fetch_synthea.execute_values") as mock_ev:
            flush_batch(conn, patients, encounters, organizations, conditions)

        # Grab the conditions argument passed to execute_values (4th call, index 3)
        calls = mock_ev.call_args_list
        inserted_conditions = calls[3][0][2]   # (conn, sql, rows)
        assert inserted_conditions[0][2] is None, "encounter_id should be nulled out"

    def test_keeps_condition_encounter_id_when_encounter_present(self):
        conditions   = [("cond-1", "pat-1", "enc-1", "active", "dx", "1234", "sys", "Pain", None, None)]
        encounters   = [("enc-1", "pat-1", "1234", "Pain", "org-1")]
        patients     = [("pat-1", "MA")]
        organizations = [("org-1", "Boston", "MA", 42.36, -71.06)]

        conn = self._make_conn()
        with patch("fetch_synthea.execute_values") as mock_ev:
            flush_batch(conn, patients, encounters, organizations, conditions)

        calls = mock_ev.call_args_list
        inserted_conditions = calls[3][0][2]
        assert inserted_conditions[0][2] == "enc-1"

    def test_filters_out_orgs_not_linked_to_any_encounter(self):
        # org-2 not referenced by any encounter → should be dropped
        encounters    = [("enc-1", "pat-1", "1234", "Pain", "org-1")]
        patients      = [("pat-1", "MA")]
        organizations = [("org-1", "Boston", "MA", 42.36, -71.06),
                         ("org-2", "Nowhere", "XX", 0.0, 0.0)]
        conditions    = []

        conn = self._make_conn()
        with patch("fetch_synthea.execute_values") as mock_ev:
            flush_batch(conn, patients, encounters, organizations, conditions)

        calls = mock_ev.call_args_list
        inserted_orgs = calls[1][0][2]   # organizations is the 2nd execute_values call
        assert len(inserted_orgs) == 1
        assert inserted_orgs[0][0] == "org-1"

    def test_returns_correct_counts(self):
        patients      = [("pat-1", "MA"), ("pat-2", "HI")]
        encounters    = [("enc-1", "pat-1", None, None, "org-1")]
        organizations = [("org-1", "Boston", "MA", 42.36, -71.06)]
        conditions    = [("cond-1", "pat-1", "enc-1", "active", "dx", "1234", "sys", "Pain", None, None)]

        conn = self._make_conn()
        with patch("fetch_synthea.execute_values"):
            np, ne, no, nc = flush_batch(conn, patients, encounters, organizations, conditions)

        assert np == 2
        assert ne == 1
        assert no == 1
        assert nc == 1

    def test_inserts_in_fk_order(self):
        """patients and orgs must be inserted before encounters, encounters before conditions."""
        patients      = [("pat-1", "MA")]
        encounters    = [("enc-1", "pat-1", None, None, "org-1")]
        organizations = [("org-1", "Boston", "MA", 42.36, -71.06)]
        conditions    = [("cond-1", "pat-1", "enc-1", "active", "dx", "1234", "sys", "Pain", None, None)]

        conn = self._make_conn()
        insert_order = []
        def fake_ev(conn, sql, rows):
            if "patients" in sql:     insert_order.append("patients")
            elif "organizations" in sql: insert_order.append("organizations")
            elif "encounters" in sql:  insert_order.append("encounters")
            elif "conditions" in sql:  insert_order.append("conditions")

        with patch("fetch_synthea.execute_values", side_effect=fake_ev):
            flush_batch(conn, patients, encounters, organizations, conditions)

        assert insert_order.index("patients")      < insert_order.index("encounters")
        assert insert_order.index("organizations") < insert_order.index("encounters")
        assert insert_order.index("encounters")    < insert_order.index("conditions")


class TestParseLocation:
    def test_full_location(self):
        r = {
            "position": {"latitude": 42.361145, "longitude": -71.057083},
            "managingOrganization": {"identifier": {"value": "org-1"}},
        }
        result = parse_location(r)
        assert result == ("org-1", 42.361145, -71.057083)

    def test_missing_org_returns_none(self):
        r = {
            "position": {"latitude": 42.36, "longitude": -71.06},
            "managingOrganization": {},
        }
        assert parse_location(r) is None

    def test_missing_lat_returns_none(self):
        r = {
            "position": {"longitude": -71.06},
            "managingOrganization": {"identifier": {"value": "org-1"}},
        }
        assert parse_location(r) is None

    def test_coordinates_rounded_to_6_decimals(self):
        r = {
            "position": {"latitude": 42.3611456789, "longitude": -71.0570834567},
            "managingOrganization": {"identifier": {"value": "org-1"}},
        }
        _, lat, lon = parse_location(r)
        assert lat == round(42.3611456789, 6)
        assert lon == round(-71.0570834567, 6)
