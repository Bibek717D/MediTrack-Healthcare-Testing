from datetime import datetime, timedelta
import pytest
import appointments
from exceptions import ValidationError, SchedulingConflict, InvalidStateError, AuthError


def test_loop_zero_iterations(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    assert appointments.get_appointment(appt_id)["status"] == "Scheduled"


def test_loop_one_iteration_no_overlap(sample_patient, future_monday_10am):
    appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )

    new_time = future_monday_10am.replace(hour=11)
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", new_time, "follow_up", 30
    )

    assert appointments.get_appointment(appt_id)["status"] == "Scheduled"


def test_loop_one_iteration_with_overlap(sample_patient, future_monday_10am):
    appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )

    overlap_time = future_monday_10am.replace(minute=15)

    with pytest.raises(SchedulingConflict):
        appointments.schedule_appointment(
            sample_patient, "provider-001", overlap_time, "follow_up", 30
        )


def test_loop_n_minus_one_iterations(sample_patient, future_monday_10am):
    base = future_monday_10am.replace(hour=8, minute=0)

    for i in range(7):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            base.replace(hour=8 + i),
            "follow_up",
            30
        )

    appt_id = appointments.schedule_appointment(
        sample_patient,
        "provider-001",
        base.replace(hour=15),
        "follow_up",
        30
    )

    assert appointments.get_appointment(appt_id)["status"] == "Scheduled"


def test_loop_n_iterations(sample_patient, future_monday_10am):
    base = future_monday_10am.replace(hour=8, minute=0)

    for i in range(8):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            base.replace(hour=8 + i),
            "follow_up",
            30
        )

    appt_id = appointments.schedule_appointment(
        sample_patient,
        "provider-001",
        base.replace(hour=16),
        "follow_up",
        30
    )

    assert appointments.get_appointment(appt_id)["status"] == "Scheduled"

def test_loop_patient_not_found(future_monday_10am):
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            "bad-patient",
            "provider-001",
            future_monday_10am,
            "follow_up",
            30
        )


def test_loop_past_time(sample_patient):
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            datetime.now() - timedelta(days=1),
            "follow_up",
            30
        )


def test_loop_weekend_rejected(sample_patient, future_monday_10am):
    weekend = future_monday_10am + timedelta(days=5)

    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            weekend,
            "follow_up",
            30
        )


def test_loop_bad_hour(sample_patient, future_monday_10am):
    early = future_monday_10am.replace(hour=7)

    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            early,
            "follow_up",
            30
        )


def test_loop_bad_type(sample_patient, future_monday_10am):
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            future_monday_10am,
            "bad_type",
            30
        )


def test_loop_bad_duration(sample_patient, future_monday_10am):
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            future_monday_10am,
            "follow_up",
            20
        )

def test_loop_cancel_missing():
    with pytest.raises(ValidationError):
        appointments.cancel_appointment("bad-id", "staff", "reason")


def test_loop_cancel_completed(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.check_in(appt_id, "staff")
    appointments.start_visit(appt_id)
    appointments.complete_appointment(appt_id, "done", "provider-001")

    with pytest.raises(InvalidStateError):
        appointments.cancel_appointment(appt_id, "staff", "reason")


def test_loop_cancel_in_progress_not_admin(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.check_in(appt_id, "staff")
    appointments.start_visit(appt_id)

    with pytest.raises(AuthError):
        appointments.cancel_appointment(appt_id, "staff", "reason", role="receptionist")


def test_loop_check_in_missing():
    with pytest.raises(ValidationError):
        appointments.check_in("bad-id", "staff")


def test_loop_check_in_wrong_state(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.cancel_appointment(appt_id, "staff", "reason")

    with pytest.raises(InvalidStateError):
        appointments.check_in(appt_id, "staff")


def test_loop_start_visit_missing():
    with pytest.raises(ValidationError):
        appointments.start_visit("bad-id")


def test_loop_start_visit_wrong_state(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )

    with pytest.raises(InvalidStateError):
        appointments.start_visit(appt_id)


def test_loop_complete_missing():
    with pytest.raises(ValidationError):
        appointments.complete_appointment("bad-id", "done", "provider-001")


def test_loop_complete_wrong_state(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )

    with pytest.raises(InvalidStateError):
        appointments.complete_appointment(appt_id, "done", "provider-001")


def test_loop_complete_wrong_provider(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.check_in(appt_id, "staff")
    appointments.start_visit(appt_id)

    with pytest.raises(AuthError):
        appointments.complete_appointment(appt_id, "done", "wrong-provider")


def test_loop_complete_empty_notes(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.check_in(appt_id, "staff")
    appointments.start_visit(appt_id)

    with pytest.raises(ValidationError):
        appointments.complete_appointment(appt_id, "   ", "provider-001")


class User:
    def __init__(self, role):
        self.role = role


def test_loop_reschedule_missing():
    with pytest.raises(ValidationError):
        appointments.reschedule_appointment(
            "bad-id",
            datetime.now() + timedelta(days=3),
            User("admin")
        )


def test_loop_reschedule_wrong_state(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )

    with pytest.raises(InvalidStateError):
        appointments.reschedule_appointment(
            appt_id,
            future_monday_10am + timedelta(days=1),
            User("admin")
        )


def test_loop_reschedule_past_time(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.cancel_appointment(appt_id, "staff", "reason")

    with pytest.raises(ValidationError):
        appointments.reschedule_appointment(
            appt_id,
            datetime.now() - timedelta(days=1),
            User("admin")
        )


def test_loop_reschedule_bad_role(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.cancel_appointment(appt_id, "staff", "reason")

    with pytest.raises(AuthError):
        appointments.reschedule_appointment(
            appt_id,
            future_monday_10am + timedelta(days=1),
            User("patient")
        )