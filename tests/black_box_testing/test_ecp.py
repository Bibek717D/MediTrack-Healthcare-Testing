import pytest
from appointments import schedule_appointment
from exceptions import ValidationError


def test_ecp_valid_new_patient(sample_patient, future_monday_10am):
    assert schedule_appointment(sample_patient, "provider001", future_monday_10am, "new_patient") is not None


def test_ecp_valid_follow_up(sample_patient, future_monday_10am):
    assert schedule_appointment(sample_patient, "provider001", future_monday_10am, "follow_up") is not None


def test_ecp_valid_urgent_care(sample_patient, future_monday_10am):
    assert schedule_appointment(sample_patient, "provider001", future_monday_10am, "urgent_care") is not None


def test_ecp_valid_procedure(sample_patient, future_monday_10am):
    assert schedule_appointment(sample_patient, "provider001", future_monday_10am, "procedure") is not None


def test_ecp_valid_telehealth(sample_patient, future_monday_10am):
    assert schedule_appointment(sample_patient, "provider001", future_monday_10am, "telehealth") is not None


def test_ecp_invalid_empty_type(sample_patient, future_monday_10am):
    with pytest.raises(ValidationError):
        schedule_appointment(sample_patient, "provider001", future_monday_10am, "")


def test_ecp_invalid_unknown_type(sample_patient, future_monday_10am):
    with pytest.raises(ValidationError):
        schedule_appointment(sample_patient, "provider001", future_monday_10am, "unknown_type")


def test_ecp_invalid_none_type(sample_patient, future_monday_10am):
    with pytest.raises(ValidationError):
        schedule_appointment(sample_patient, "provider001", future_monday_10am, None)

from patients import register_patient, search_patients
from datetime import date


def test_search_patients_exact_name_match():
    register_patient("Ana", "Gomez", date(1990, 5, 1), "8175550001", "ana@test.com")
    results = search_patients("Ana Gomez")
    assert len(results) >= 1


def test_search_patients_partial_name_match():
    register_patient("Ana", "Gomez", date(1990, 5, 1), "8175550001", "ana@test.com")
    results = search_patients("Ana")
    assert len(results) >= 1


def test_search_patients_valid_no_result():
    results = search_patients("Nobody")
    assert results == []


def test_search_patients_empty_query():
    results = search_patients("")
    assert results == []


def test_search_patients_none_query():
    results = search_patients(None)
    assert results == []


def test_search_patients_sql_like_query_sanitized():
    register_patient("Ana", "Gomez", date(1990, 5, 1), "8175550001", "ana@test.com")
    results = search_patients("'; DROP TABLE patients;--")
    assert isinstance(results, list)