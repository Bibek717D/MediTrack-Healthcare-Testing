import pytest

from patients import deactivate_patient, search_patients
from appointments import cancel_appointment, mark_no_show
from billing import create_bill, apply_discount, apply_insurance

from patients import add_patient, get_patient
from appointments import schedule_appointment, check_in, get_appointment
from records import add_diagnosis, get_record_by_appointment
from billing import create_invoice, process_payment
from database import get_connection


def test_complete_urgent_care_visit_system_workflow(fresh_db):
    # Step 1: Register patient
    patient_id = add_patient(
        "Carlos",
        "Rivera",
        "1988-04-12",
        phone="8175551234",
        email="crivera@test.com",
        db_path=fresh_db
    )

    patient = get_patient(patient_id, db_path=fresh_db)
    assert patient is not None
    assert patient["first_name"] == "Carlos"
    assert patient["last_name"] == "Rivera"
    assert patient["is_active"] == 1

    # Step 2: Schedule urgent appointment
    appointment_id = schedule_appointment(
        patient_id,
        "2026-07-13 10:00:00",
        "urgent",
        db_path=fresh_db
    )

    appt = get_appointment(appointment_id, db_path=fresh_db)
    assert appt is not None
    assert appt["patient_id"] == patient_id
    assert appt["appointment_type"] == "urgent"
    assert appt["status"] == "scheduled"

    # Step 3: Check in patient
    checked_in = check_in(appointment_id, db_path=fresh_db)
    appt = get_appointment(appointment_id, db_path=fresh_db)

    assert checked_in is True
    assert appt["status"] == "checked_in"

    # Step 4/5/6/7/8: Add diagnosis/record and prescription text
    record = add_diagnosis(
        patient_id=patient_id,
        appointment_id=appointment_id,
        diagnosis="Unspecified chest pain",
        notes="Chief complaint: chest pain. ICD code R07.9. Primary diagnosis.",
        prescriptions="aspirin 81mg, once_daily, 30 days",
        db_path=fresh_db
    )

    assert record["record_id"] is not None
    assert record["patient_id"] == patient_id
    assert record["appointment_id"] == appointment_id
    assert record["diagnosis"] == "Unspecified chest pain"
    assert record["prescriptions"] == "aspirin 81mg, once_daily, 30 days"
    assert record["action"] == "inserted"

    saved_record = get_record_by_appointment(appointment_id, db_path=fresh_db)
    appt = get_appointment(appointment_id, db_path=fresh_db)

    assert saved_record is not None
    assert saved_record["diagnosis"] == "Unspecified chest pain"
    assert appt["status"] == "completed"

    # Step 9: Create invoice
    invoice_id = create_invoice(
        patient_id=patient_id,
        appointment_id=appointment_id,
        amount=200.00,
        notes="Service code 99214",
        db_path=fresh_db
    )

    conn = get_connection(fresh_db)
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,))
    invoice = cur.fetchone()
    conn.close()

    assert invoice is not None
    assert invoice["patient_id"] == patient_id
    assert invoice["appointment_id"] == appointment_id
    assert invoice["amount"] == 200.00

    # Step 10: Process cash payment
    billing_id = None

    conn = get_connection(fresh_db)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO billing (appointment_id, patient_id, amount_due)
        VALUES (?, ?, ?)
        """,
        (appointment_id, patient_id, 200.00)
    )
    billing_id = cur.lastrowid
    conn.commit()
    conn.close()

    payment_result = process_payment(
        billing_id=billing_id,
        amount_paid=200.00,
        payment_method="cash",
        db_path=fresh_db
    )

    assert payment_result["billing_id"] == billing_id
    assert payment_result["amount_due"] == 200.00
    assert payment_result["amount_paid"] == 200.00
    assert payment_result["status"] == "paid"

def test_coverage_patient_validation_and_search(fresh_db):
    with pytest.raises(ValueError):
        add_patient("", "Smith", "1990-01-01", db_path=fresh_db)

    with pytest.raises(ValueError):
        add_patient("John", "", "1990-01-01", db_path=fresh_db)

    with pytest.raises(ValueError):
        add_patient("John", "Smith", "", db_path=fresh_db)

    pid = add_patient("Maya", "Patel", "1991-04-10", db_path=fresh_db)
    results = search_patients("Maya", db_path=fresh_db)

    assert len(results) == 1
    assert results[0]["patient_id"] == pid


def test_coverage_deactivate_patient_not_found(fresh_db):
    with pytest.raises(ValueError, match="not found"):
        deactivate_patient(999, db_path=fresh_db)


def test_coverage_appointment_validation_paths(fresh_db):
    pid = add_patient("Tom", "Hall", "1980-01-01", db_path=fresh_db)

    with pytest.raises(ValueError, match="Invalid appointment_type"):
        schedule_appointment(pid, "2026-07-14 09:00:00", "bad_type", db_path=fresh_db)

    with pytest.raises(ValueError, match="scheduled_time is required"):
        schedule_appointment(pid, "", "checkup", db_path=fresh_db)

    with pytest.raises(ValueError, match="Appointment 999 not found"):
        check_in(999, db_path=fresh_db)


def test_coverage_cancel_and_no_show_paths(fresh_db):
    pid = add_patient("Nina", "Roy", "1993-02-02", db_path=fresh_db)

    appt_id = schedule_appointment(
        pid, "2026-07-14 10:00:00", "checkup", db_path=fresh_db
    )

    cancel_result = cancel_appointment(appt_id, "patient", db_path=fresh_db)

    assert cancel_result["appointment_id"] == appt_id
    assert cancel_result["cancelled_by"] == "patient"

    with pytest.raises(ValueError, match="Cannot cancel appointment"):
        cancel_appointment(appt_id, "patient", db_path=fresh_db)

    appt2 = schedule_appointment(
        pid, "2026-07-14 11:00:00", "follow_up", db_path=fresh_db
    )

    assert mark_no_show(appt2, db_path=fresh_db) is True

    with pytest.raises(ValueError, match="current status"):
        mark_no_show(appt2, db_path=fresh_db)


def test_coverage_billing_validation_and_payment_paths(fresh_db):
    pid = add_patient("Alex", "Kim", "1990-03-03", db_path=fresh_db)
    appt_id = schedule_appointment(
        pid, "2026-07-15 09:00:00", "checkup", db_path=fresh_db
    )

    with pytest.raises(ValueError, match="amount_due cannot be negative"):
        create_bill(appt_id, pid, -10, db_path=fresh_db)

    bill_id = create_bill(appt_id, pid, 300.00, db_path=fresh_db)

    partial = process_payment(
        bill_id, 100.00, "card", db_path=fresh_db
    )
    assert partial["status"] == "partial"

    with pytest.raises(ValueError, match="Invalid payment_method"):
        process_payment(bill_id, 50.00, "bitcoin", db_path=fresh_db)

    with pytest.raises(NotImplementedError):
        apply_discount(bill_id, 10, db_path=fresh_db)


def test_coverage_billing_invoice_and_insurance_errors(fresh_db):
    pid = add_patient("Sara", "Green", "1992-05-05", db_path=fresh_db)
    appt_id = schedule_appointment(
        pid, "2026-07-15 10:00:00", "urgent", db_path=fresh_db
    )

    with pytest.raises(ValueError, match="Invalid invoice status"):
        create_invoice(pid, appt_id, 100.00, status="BadStatus", db_path=fresh_db)

    invoice_id = create_invoice(
        pid, appt_id, 500.00, status="Paid", db_path=fresh_db
    )

    with pytest.raises(ValueError, match="Cannot apply insurance"):
        apply_insurance(invoice_id, "Aetna", 50, db_path=fresh_db)

    with pytest.raises(LookupError):
        apply_insurance(999, "Aetna", 50, db_path=fresh_db)