import pytest
from datetime import date

from patients import register_patient
from appointments import schedule_appointment
from exceptions import ValidationError


VALID_LAST = "Smith"
VALID_DOB = date(1990, 1, 1)
VALID_PHONE = "8175550001"
VALID_EMAIL = "test@example.com"


def test_bva_name_min_minus_1():
    """BVA name min-1: length 0 should fail."""
    with pytest.raises(ValidationError):
        register_patient("", VALID_LAST, VALID_DOB, VALID_PHONE, VALID_EMAIL)


def test_bva_name_min():
    """BVA name min: length 1 should pass."""
    pid = register_patient("A", VALID_LAST, VALID_DOB, VALID_PHONE, VALID_EMAIL)
    assert pid is not None


def test_bva_name_min_plus_1():
    """BVA name min+1: length 2 should pass."""
    pid = register_patient("Jo", VALID_LAST, VALID_DOB, VALID_PHONE, VALID_EMAIL)
    assert pid is not None


def test_bva_name_max_minus_1():
    """BVA name max-1: length 49 should pass."""
    pid = register_patient("A" * 49, VALID_LAST, VALID_DOB, VALID_PHONE, VALID_EMAIL)
    assert pid is not None


def test_bva_name_max():
    """BVA name max: length 50 should pass."""
    pid = register_patient("A" * 50, VALID_LAST, VALID_DOB, VALID_PHONE, VALID_EMAIL)
    assert pid is not None


def test_bva_name_max_plus_1():
    """BVA name max+1: length 51 should fail."""
    with pytest.raises(ValidationError):
        register_patient("A" * 51, VALID_LAST, VALID_DOB, VALID_PHONE, VALID_EMAIL)

def test_bva_phone_9_digits():
    with pytest.raises(ValidationError):
        register_patient(
            "John",
            VALID_LAST,
            VALID_DOB,
            "123456789",
            VALID_EMAIL
        )


def test_bva_phone_10_digits():
    pid = register_patient(
        "John",
        VALID_LAST,
        VALID_DOB,
        "1234567890",
        VALID_EMAIL
    )

    assert pid is not None


def test_bva_phone_11_digits():
    with pytest.raises(ValidationError):
        register_patient(
            "John",
            VALID_LAST,
            VALID_DOB,
            "12345678901",
            VALID_EMAIL
        )

    from appointments import schedule_appointment


def test_duration_15_valid(sample_patient, future_monday_10am):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up",
        15
    )
    assert appt_id is not None


def test_duration_30_valid(sample_patient, future_monday_10am):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up",
        30
    )
    assert appt_id is not None


def test_duration_45_valid(sample_patient, future_monday_10am):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up",
        45
    )
    assert appt_id is not None


def test_duration_60_valid(sample_patient, future_monday_10am):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up",
        60
    )
    assert appt_id is not None


def test_duration_14_invalid(sample_patient, future_monday_10am):
    with pytest.raises(ValidationError):
        schedule_appointment(
            sample_patient,
            "provider001",
            future_monday_10am,
            "follow_up",
            14
        )


def test_duration_61_invalid(sample_patient, future_monday_10am):
    with pytest.raises(ValidationError):
        schedule_appointment(
            sample_patient,
            "provider001",
            future_monday_10am,
            "follow_up",
            61
        )