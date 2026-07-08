import pytest

from patients import add_patient, get_patient, deactivate_patient
from appointments import schedule_appointment, get_appointment, cancel_appointment
from billing import create_invoice, apply_insurance
from database import get_connection


def test_tc_int_1_register_patient_schedule_appointment(fresh_db):
    patient_id = add_patient(
        "Carlos", "Rivera", "1988-04-12",
        phone="8175551234",
        email="crivera@test.com",
        db_path=fresh_db
    )

    appointment_id = schedule_appointment(
        patient_id,
        "2026-07-06 10:00:00",
        "urgent",
        db_path=fresh_db
    )

    appt = get_appointment(appointment_id, db_path=fresh_db)

    assert appt is not None
    assert appt["patient_id"] == patient_id
    assert appt["status"] == "scheduled"


def test_tc_int_2_deactivate_patient_then_schedule_fails(fresh_db):
    patient_id = add_patient("Ana", "Gomez", "1990-05-01", db_path=fresh_db)
    deactivate_patient(patient_id, db_path=fresh_db)

    with pytest.raises(ValueError, match="inactive"):
        schedule_appointment(
            patient_id,
            "2026-07-06 10:00:00",
            "checkup",
            db_path=fresh_db
        )


def test_tc_int_3_invalid_patient_schedule_fails(fresh_db):
    with pytest.raises(ValueError, match="does not exist"):
        schedule_appointment(
            999,
            "2026-07-06 10:00:00",
            "checkup",
            db_path=fresh_db
        )


def test_tc_int_4_cancel_appointment_patient_still_active(fresh_db):
    patient_id = add_patient("Bob", "Smith", "1985-03-15", db_path=fresh_db)

    appointment_id = schedule_appointment(
        patient_id,
        "2026-07-06 11:00:00",
        "follow_up",
        db_path=fresh_db
    )

    cancel_appointment(appointment_id, cancelled_by="patient", db_path=fresh_db)

    patient = get_patient(patient_id, db_path=fresh_db)
    appt = get_appointment(appointment_id, db_path=fresh_db)

    assert patient["is_active"] == 1
    assert appt["status"] == "cancelled"


def test_tc_int_5_duplicate_patient_records_created(fresh_db):
    first_id = add_patient("Sam", "Lee", "1995-01-01", db_path=fresh_db)
    second_id = add_patient("Sam", "Lee", "1995-01-01", db_path=fresh_db)

    first_patient = get_patient(first_id, db_path=fresh_db)
    second_patient = get_patient(second_id, db_path=fresh_db)

    assert first_id != second_id
    assert first_patient is not None
    assert second_patient is not None
    assert first_patient["first_name"] == second_patient["first_name"]
    assert first_patient["date_of_birth"] == second_patient["date_of_birth"]


def test_tc_int_6_create_invoice_linked_to_correct_appointment(fresh_db):
    patient_id = add_patient(
        "John",
        "Doe",
        "1990-01-01",
        db_path=fresh_db
    )

    appointment_id = schedule_appointment(
        patient_id,
        "2026-07-08 09:00:00",
        "checkup",
        db_path=fresh_db
    )

    invoice_id = create_invoice(
        patient_id=patient_id,
        appointment_id=appointment_id,
        amount=250.00,
        notes="Office Visit",
        db_path=fresh_db
    )

    conn = get_connection(fresh_db)
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,))
    invoice = cur.fetchone()
    conn.close()

    assert invoice is not None
    assert invoice["appointment_id"] == appointment_id
    assert invoice["patient_id"] == patient_id


def test_tc_int_7_invalid_invoice_amount(fresh_db):
    patient_id = add_patient(
        "Amy",
        "Jones",
        "1994-02-10",
        db_path=fresh_db
    )

    appointment_id = schedule_appointment(
        patient_id,
        "2026-07-08 10:00:00",
        "checkup",
        db_path=fresh_db
    )

    with pytest.raises(ValueError, match="Invoice amount must be greater than zero"):
        create_invoice(
            patient_id=patient_id,
            appointment_id=appointment_id,
            amount=0,
            db_path=fresh_db
        )


def test_tc_int_8_apply_insurance_updates_invoice(fresh_db):
    patient_id = add_patient(
        "Chris",
        "Brown",
        "1992-06-15",
        db_path=fresh_db
    )

    appointment_id = schedule_appointment(
        patient_id,
        "2026-07-08 11:00:00",
        "urgent",
        db_path=fresh_db
    )

    invoice_id = create_invoice(
        patient_id=patient_id,
        appointment_id=appointment_id,
        amount=400.00,
        db_path=fresh_db
    )

    result = apply_insurance(
        invoice_id,
        "BlueCross",
        75,
        db_path=fresh_db
    )

    conn = get_connection(fresh_db)
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,))
    invoice = cur.fetchone()
    conn.close()

    assert result["insurance_applied"] is True
    assert result["coverage_pct"] == 75
    assert result["insurance_covers"] == 300.00
    assert result["balance_due"] == 100.00
    assert invoice["insurance_applied"] == 1
    assert invoice["balance_due"] == 100.00