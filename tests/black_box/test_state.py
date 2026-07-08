from appointments import (
    schedule_appointment,
    get_appointment,
    check_in,
    start_visit,
    complete_appointment,
    cancel_appointment
)


def test_scheduled_state(sample_patient, future_monday_10am):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up"
    )

    assert get_appointment(appt_id)["status"] == "Scheduled"


def test_checkedin_state(sample_patient, future_monday_10am):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up"
    )

    check_in(appt_id, "receptionist")

    assert get_appointment(appt_id)["status"] == "CheckedIn"


def test_inprogress_state(sample_patient, future_monday_10am):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up"
    )

    check_in(appt_id, "receptionist")
    start_visit(appt_id)

    assert get_appointment(appt_id)["status"] == "InProgress"


def test_completed_state(sample_patient, future_monday_10am):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up"
    )

    check_in(appt_id, "receptionist")
    start_visit(appt_id)

    complete_appointment(
        appt_id,
        notes="Patient doing well",
        provider_id="provider001"
    )

    assert get_appointment(appt_id)["status"] == "Completed"
  
def test_cancelled_state(sample_patient, future_monday_10am):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up"
    )

    cancel_appointment(
        appt_id,
        cancelled_by="receptionist",
        reason="Patient requested cancellation"
    )

    assert get_appointment(appt_id)["status"] == "Cancelled"


def test_transition_pair_scheduled_checkedin_inprogress(
    sample_patient,
    future_monday_10am
):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up"
    )

    check_in(appt_id, "receptionist")

    assert get_appointment(appt_id)["status"] == "CheckedIn"

    start_visit(appt_id)

    assert get_appointment(appt_id)["status"] == "InProgress"

import pytest

def test_transition_pair_scheduled_cancelled(
    sample_patient,
    future_monday_10am
):
    appt_id = schedule_appointment(
        sample_patient,
        "provider001",
        future_monday_10am,
        "follow_up"
    )

    cancel_appointment(
        appt_id,
        cancelled_by="receptionist",
        reason="Patient requested cancellation"
    )

    assert get_appointment(appt_id)["status"] == "Cancelled"