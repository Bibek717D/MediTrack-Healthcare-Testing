import pytest
from datetime import datetime, timedelta

import appointments
from exceptions import ValidationError
from unittest.mock import MagicMock

def test_patient_not_found():
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            "bad-patient-id",
            "provider-001",
            datetime.now() + timedelta(days=1),
            "follow_up",
            30
        )


def test_time_in_past(sample_patient):
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            datetime.now() - timedelta(days=1),
            "follow_up",
            30
        )


def test_invalid_type(sample_patient, future_monday_10am):
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            future_monday_10am,
            "bad_type",
            30
        )


def test_invalid_duration(sample_patient, future_monday_10am):
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            future_monday_10am,
            "follow_up",
            20
        )


def test_valid_appointment(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient,
        "provider-001",
        future_monday_10am,
        "follow_up",
        30
    )

    appt = appointments.get_appointment(appt_id)
    assert appt["status"] == "Scheduled"

from exceptions import InvalidStateError, AuthError


def test_weekend_rejected(sample_patient, future_monday_10am):
    weekend = future_monday_10am.replace(day=future_monday_10am.day + 5)
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient, "provider-001", weekend, "follow_up", 30
        )


def test_outside_hours_rejected(sample_patient, future_monday_10am):
    early = future_monday_10am.replace(hour=7)
    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient, "provider-001", early, "follow_up", 30
        )


def test_cancel_missing_appointment():
    with pytest.raises(ValidationError):
        appointments.cancel_appointment("bad-id", "staff", "reason")


def test_check_in_wrong_state(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.cancel_appointment(appt_id, "staff", "reason")

    with pytest.raises(InvalidStateError):
        appointments.check_in(appt_id, "staff")


def test_complete_wrong_provider(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.check_in(appt_id, "staff")
    appointments.start_visit(appt_id)

    with pytest.raises(AuthError):
        appointments.complete_appointment(appt_id, "done", "wrong-provider")

class User:
    def __init__(self, role):
        self.role = role


def test_start_visit_missing():
    with pytest.raises(ValidationError):
        appointments.start_visit("bad-id")


def test_start_visit_wrong_state(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )

    with pytest.raises(InvalidStateError):
        appointments.start_visit(appt_id)


def test_complete_missing():
    with pytest.raises(ValidationError):
        appointments.complete_appointment("bad-id", "done", "provider-001")


def test_complete_empty_notes(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.check_in(appt_id, "staff")
    appointments.start_visit(appt_id)

    with pytest.raises(ValidationError):
        appointments.complete_appointment(appt_id, "   ", "provider-001")


def test_reschedule_missing():
    with pytest.raises(ValidationError):
        appointments.reschedule_appointment("bad-id", datetime.now() + timedelta(days=2), User("admin"))


def test_reschedule_wrong_state(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )

    with pytest.raises(InvalidStateError):
        appointments.reschedule_appointment(appt_id, future_monday_10am + timedelta(days=1), User("admin"))


def test_reschedule_unauthorized(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.cancel_appointment(appt_id, "staff", "reason")

    with pytest.raises(AuthError):
        appointments.reschedule_appointment(appt_id, future_monday_10am + timedelta(days=1), User("patient"))


def test_reschedule_success(sample_patient, future_monday_10am):
    appt_id = appointments.schedule_appointment(
        sample_patient, "provider-001", future_monday_10am, "follow_up", 30
    )
    appointments.cancel_appointment(appt_id, "staff", "reason")

    new_id = appointments.reschedule_appointment(
        appt_id, future_monday_10am + timedelta(days=1), User("admin")
    )

    assert appointments.get_appointment(new_id)["status"] == "Scheduled"


def test_short_circuit_weekend(sample_patient):
    fake_dt = MagicMock()
    fake_dt.__le__.return_value = False
    fake_dt.weekday.return_value = 6

    type(fake_dt).hour = property(
        lambda self: pytest.fail("hour should not be evaluated")
    )

    with pytest.raises(ValidationError):
        appointments.schedule_appointment(
            sample_patient,
            "provider-001",
            fake_dt,
            "follow_up",
            30
        )
