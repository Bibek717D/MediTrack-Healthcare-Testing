from datetime import datetime, timedelta
import pytest

from patients import add_patient, search_patients
from appointments import schedule_appointment, cancel_appointment
from billing import create_bill, process_payment
from database import get_connection


def test_r_appt_late_cancellation_sets_late_flag(fresh_db):
    """R-APPT-LATE: Late cancellation within 24 hours should set is_late_cancellation=True."""
    patient_id = add_patient("Late", "Cancel", "1999-01-01", db_path=fresh_db)
    soon = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

    appointment_id = schedule_appointment(
        patient_id,
        soon,
        "checkup",
        db_path=fresh_db
    )

    result = cancel_appointment(
        appointment_id,
        "admin",
        db_path=fresh_db
    )

    assert result["is_late_cancellation"] is True


def test_r_bill_void_payment_not_allowed(fresh_db):
    """R-BILL-VOID: Cannot process payment on a voided billing record."""
    patient_id = add_patient("Void", "Bill", "1999-01-01", db_path=fresh_db)

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

    conn = get_connection(fresh_db)
    cur = conn.cursor()
    cur.execute(
        "UPDATE billing SET status = 'voided' WHERE billing_id = ?",
        (billing_id,)
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError):
        process_payment(
            billing_id,
            50.00,
            "cash",
            db_path=fresh_db
        )


def test_r_pat_search_whitespace_query_rejected(fresh_db):
    """R-PAT-SEARCH-SEC: Whitespace-only search should not return unintended records."""
    add_patient("Alice", "Smith", "1990-01-01", db_path=fresh_db)

    results = search_patients("   ", db_path=fresh_db)

    assert results == []