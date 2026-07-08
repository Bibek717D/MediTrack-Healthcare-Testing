import sqlite3
import pytest

from patients import add_patient, search_patients, get_patient
from database import get_connection


SQL_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE patients--",
    "' UNION SELECT * FROM billing--",
    "admin'--",
    "1; SELECT * FROM records WHERE '1'='1",
]


def _patients_table_exists(db_path):
    """Return True if the patients table still exists."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='patients'"
    )
    result = cur.fetchone()
    conn.close()
    return result is not None


def _payload_reflected(payload, returned_data):
    """Check whether the exact payload appears in returned record fields."""
    if returned_data is None:
        return False

    if isinstance(returned_data, dict):
        return any(payload in str(value) for value in returned_data.values())

    if isinstance(returned_data, (list, tuple)):
        for item in returned_data:
            if isinstance(item, dict):
                if any(payload in str(value) for value in item.values()):
                    return True
            else:
                if payload in str(item):
                    return True

    return payload in str(returned_data)


@pytest.mark.parametrize("payload", SQL_PAYLOADS)
def test_search_patients_sql_injection_payloads(fresh_db, payload):
    """search_patients() should safely handle SQL injection payloads."""
    add_patient("Safe", "Patient", "1990-01-01", db_path=fresh_db)

    try:
        results = search_patients(payload, db_path=fresh_db)
    except Exception as exc:
        pytest.fail(f"search_patients crashed for payload {payload!r}: {exc}")

    assert _patients_table_exists(fresh_db)
    assert not _payload_reflected(payload, results)


@pytest.mark.parametrize("payload", SQL_PAYLOADS)
def test_get_patient_sql_injection_payloads(fresh_db, payload):
    """get_patient() should safely handle SQL injection payloads."""
    add_patient("Safe", "Patient", "1990-01-01", db_path=fresh_db)

    try:
        result = get_patient(payload, db_path=fresh_db)
    except Exception as exc:
        pytest.fail(f"get_patient crashed for payload {payload!r}: {exc}")

    assert _patients_table_exists(fresh_db)
    assert not _payload_reflected(payload, result)


from appointments import schedule_appointment, check_in, cancel_appointment
from records import add_diagnosis
from billing import create_bill, process_payment
from patients import deactivate_patient


def test_inactive_patient_cannot_schedule_appointment(fresh_db):
    """A01 Broken Access Control: inactive patient should not be allowed to schedule."""
    patient_id = add_patient("Inactive", "User", "1990-01-01", db_path=fresh_db)
    deactivate_patient(patient_id, db_path=fresh_db)

    with pytest.raises(ValueError):
        schedule_appointment(
            patient_id,
            "2026-07-01 09:00:00",
            "checkup",
            db_path=fresh_db
        )


def test_wrong_patient_cannot_receive_diagnosis_for_other_patient_appointment(fresh_db):
    """A01 Broken Access Control: patient cannot use another patient's appointment."""
    patient_a = add_patient("Patient", "A", "1990-01-01", db_path=fresh_db)
    patient_b = add_patient("Patient", "B", "1991-01-01", db_path=fresh_db)

    appointment_id = schedule_appointment(
        patient_a,
        "2026-07-01 09:00:00",
        "checkup",
        db_path=fresh_db
    )
    check_in(appointment_id, db_path=fresh_db)

    with pytest.raises(ValueError):
        add_diagnosis(
            patient_b,
            appointment_id,
            "Flu",
            db_path=fresh_db
        )


def test_cancelled_appointment_cannot_receive_diagnosis(fresh_db):
    """A01 Broken Access Control: cancelled appointment should not allow diagnosis entry."""
    patient_id = add_patient("Cancel", "Secure", "1990-01-01", db_path=fresh_db)

    appointment_id = schedule_appointment(
        patient_id,
        "2026-07-01 09:00:00",
        "checkup",
        db_path=fresh_db
    )

    cancel_appointment(appointment_id, "patient", db_path=fresh_db)

    with pytest.raises(ValueError):
        add_diagnosis(
            patient_id,
            appointment_id,
            "Flu",
            db_path=fresh_db
        )


def test_invalid_payment_method_rejected(fresh_db):
    """A07 Authentication Failure: invalid/unsupported payment method should be rejected."""
    patient_id = add_patient("Pay", "Secure", "1990-01-01", db_path=fresh_db)

    appointment_id = schedule_appointment(
        patient_id,
        "2026-07-01 09:00:00",
        "checkup",
        db_path=fresh_db
    )

    billing_id = create_bill(
        appointment_id,
        patient_id,
        100.00,
        db_path=fresh_db
    )

    with pytest.raises(ValueError):
        process_payment(
            billing_id,
            50.00,
            "bitcoin",
            db_path=fresh_db
        )


def test_zero_payment_without_insurance_rejected(fresh_db):
    """A07 Authentication Failure: zero payment without insurance should be rejected."""
    patient_id = add_patient("Zero", "Payment", "1990-01-01", db_path=fresh_db)

    appointment_id = schedule_appointment(
        patient_id,
        "2026-07-01 09:00:00",
        "checkup",
        db_path=fresh_db
    )

    billing_id = create_bill(
        appointment_id,
        patient_id,
        100.00,
        db_path=fresh_db
    )

    with pytest.raises(ValueError):
        process_payment(
            billing_id,
            0.00,
            "cash",
            insurance_covered=False,
            db_path=fresh_db
        )