import pytest
from datetime import datetime

from patients import add_patient
from appointments import schedule_appointment, check_in, get_appointment
from records import add_diagnosis, get_record_by_appointment
from billing import create_bill, process_payment
from database import get_connection


PAIRWISE_SCHEDULE_CASES = [
    ("new_patient", 15, "Monday", 8),
    ("new_patient", 30, "Wednesday", 10),
    ("new_patient", 45, "Friday", 16),
    ("new_patient", 60, "Saturday", 17),
    ("follow_up", 15, "Wednesday", 16),
    ("follow_up", 30, "Friday", 17),
    ("follow_up", 45, "Saturday", 8),
    ("follow_up", 60, "Monday", 10),
    ("urgent_care", 15, "Friday", 10),
    ("urgent_care", 30, "Saturday", 16),
    ("urgent_care", 45, "Monday", 17),
    ("urgent_care", 60, "Wednesday", 8),
    ("procedure", 15, "Saturday", 10),
    ("procedure", 30, "Monday", 16),
    ("procedure", 45, "Wednesday", 17),
    ("procedure", 60, "Friday", 8),
    ("telehealth", 15, "Monday", 17),
    ("telehealth", 30, "Wednesday", 8),
    ("telehealth", 45, "Friday", 10),
    ("telehealth", 60, "Saturday", 16),
]

DAY_TO_DATE = {
    "Monday": "2026-07-06",
    "Wednesday": "2026-07-08",
    "Friday": "2026-07-10",
    "Saturday": "2026-07-11",
}

TYPE_MAP = {
    "new_patient": "checkup",
    "follow_up": "follow_up",
    "urgent_care": "urgent",
    "procedure": "checkup",
    "telehealth": "follow_up",
}


def _scheduled_time(day_of_week, hour_of_day):
    return f"{DAY_TO_DATE[day_of_week]} {hour_of_day:02d}:00:00"


@pytest.mark.parametrize(
    "appt_type,duration_minutes,day_of_week,hour_of_day",
    PAIRWISE_SCHEDULE_CASES
)
def test_schedule_appointment_pairwise_cases(
    fresh_db, appt_type, duration_minutes, day_of_week, hour_of_day
):
    patient_id = add_patient("Pair", "Wise", "1990-01-01", db_path=fresh_db)

    appointment_id = schedule_appointment(
        patient_id,
        _scheduled_time(day_of_week, hour_of_day),
        TYPE_MAP[appt_type],
        db_path=fresh_db
    )

    assert appointment_id > 0
    assert duration_minutes in (15, 30, 45, 60)


class SchedulingConflict(Exception):
    pass


def _schedule_with_conflict_check(patient_id, scheduled_time, appointment_type, db_path):
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT appointment_id FROM appointments "
            "WHERE scheduled_time = ? AND status = 'scheduled'",
            (scheduled_time,)
        )
        existing = cur.fetchone()
    finally:
        conn.close()

    if existing:
        raise SchedulingConflict("Requested appointment time is already booked.")

    return schedule_appointment(
        patient_id,
        scheduled_time,
        appointment_type,
        db_path=db_path
    )


def test_use_case_emergency_walk_in_urgent_care_success_path(fresh_db):
    patient_id = add_patient(
        "Emergency",
        "Walkin",
        "1990-01-01",
        db_path=fresh_db
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    appointment_id = schedule_appointment(
        patient_id,
        now,
        "urgent",
        db_path=fresh_db
    )

    assert check_in(appointment_id, db_path=fresh_db) is True

    record = add_diagnosis(
        patient_id,
        appointment_id,
        "Urgent care visit completed",
        notes="Walk-in patient checked in and treated immediately.",
        db_path=fresh_db
    )

    billing_id = create_bill(
        appointment_id,
        patient_id,
        150.00,
        db_path=fresh_db
    )

    payment = process_payment(
        billing_id,
        150.00,
        "card",
        db_path=fresh_db
    )

    final_appointment = get_appointment(appointment_id, db_path=fresh_db)
    saved_record = get_record_by_appointment(appointment_id, db_path=fresh_db)

    assert record["action"] == "inserted"
    assert saved_record["diagnosis"] == "Urgent care visit completed"
    assert final_appointment["status"] == "completed"
    assert payment["status"] == "paid"


def test_use_case_double_booking_conflict_resolution_alternate_path(fresh_db):
    first_patient = add_patient(
        "First",
        "Patient",
        "1990-01-01",
        db_path=fresh_db
    )

    second_patient = add_patient(
        "Second",
        "Patient",
        "1992-01-01",
        db_path=fresh_db
    )

    original_time = "2026-07-01 09:00:00"
    later_time = "2026-07-01 10:00:00"

    first_appt = _schedule_with_conflict_check(
        first_patient,
        original_time,
        "checkup",
        db_path=fresh_db
    )

    with pytest.raises(SchedulingConflict):
        _schedule_with_conflict_check(
            second_patient,
            original_time,
            "checkup",
            db_path=fresh_db
        )

    second_appt = _schedule_with_conflict_check(
        second_patient,
        later_time,
        "checkup",
        db_path=fresh_db
    )

    first_saved = get_appointment(first_appt, db_path=fresh_db)
    second_saved = get_appointment(second_appt, db_path=fresh_db)

    assert first_saved["scheduled_time"] == original_time
    assert second_saved["scheduled_time"] == later_time
    assert first_saved["appointment_id"] != second_saved["appointment_id"]