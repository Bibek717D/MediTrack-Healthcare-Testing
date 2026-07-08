"""MediTrack — Module 2: Appointment Scheduling."""
import uuid
from datetime import datetime, timedelta
from config import (CLINIC_OPEN_HOUR, CLINIC_CLOSE_HOUR, VALID_APPOINTMENT_TYPES,
                    VALID_DURATIONS, LATE_CANCEL_HOURS)
from exceptions import ValidationError, SchedulingConflict, InvalidStateError, AuthError

_appointments = {}


def _overlaps(existing: dict, new_dt: datetime, new_dur: int) -> bool:
    """Return True if new appointment overlaps with existing."""
    ex_start = existing['appt_datetime']
    ex_end = ex_start + timedelta(minutes=existing['duration_minutes'])
    new_end = new_dt + timedelta(minutes=new_dur)
    return not (new_end <= ex_start or new_dt >= ex_end)


def schedule_appointment(patient_id: str, provider_id: str, appt_dt: datetime,
                          appt_type: str, duration_minutes: int = 30) -> str:
    """Schedule a new appointment. Returns appointment_id.

    Raises:
        ValidationError: for invalid inputs or past/outside-hours datetime
        SchedulingConflict: if provider is already booked at that time
    """
    from patients import get_patient
    if get_patient(patient_id) is None:
        raise ValidationError("Patient not found")

    if appt_dt <= datetime.now():
        raise ValidationError("Appointment must be scheduled in the future")

    # Clinic hours: Mon–Fri (weekday 0–4), 8:00–16:59
    if appt_dt.weekday() >= 5 or not (CLINIC_OPEN_HOUR <= appt_dt.hour < CLINIC_CLOSE_HOUR):
        raise ValidationError(
            f"Appointment must be Mon–Fri {CLINIC_OPEN_HOUR}:00–{CLINIC_CLOSE_HOUR}:00")

    if appt_type not in VALID_APPOINTMENT_TYPES:
        raise ValidationError(f"Invalid appt_type: {appt_type}. Valid: {VALID_APPOINTMENT_TYPES}")

    if duration_minutes not in VALID_DURATIONS:
        raise ValidationError(f"duration_minutes must be one of {VALID_DURATIONS}")

    # Check for provider double-booking
    provider_appts = [a for a in _appointments.values()
                      if a['provider_id'] == provider_id
                      and a['status'] == 'Scheduled'
                      and a['appt_datetime'].date() == appt_dt.date()]

    for existing in provider_appts:
        if _overlaps(existing, appt_dt, duration_minutes):
            raise SchedulingConflict(
                f"Provider {provider_id} already has an appointment at {appt_dt}")

    appt_id = str(uuid.uuid4())
    _appointments[appt_id] = {
        'appt_id': appt_id,
        'patient_id': patient_id,
        'provider_id': provider_id,
        'appt_datetime': appt_dt,
        'appt_type': appt_type,
        'duration_minutes': duration_minutes,
        'status': 'Scheduled',
        'checked_in_by': None,
        'checked_in_at': None,
        'is_late_cancellation': False,
        'created_at': datetime.now(),
    }
    return appt_id


def cancel_appointment(appt_id: str, cancelled_by: str, reason: str,
                       role: str = 'receptionist') -> None:
    """Cancel a scheduled or in-progress appointment."""
    appt = _appointments.get(appt_id)
    if appt is None:
        raise ValidationError(f"Appointment {appt_id} not found")
    if appt['status'] == 'Completed':
        raise InvalidStateError("Cannot cancel a completed appointment")
    if appt['status'] in ('Cancelled', 'NoShow'):
        raise InvalidStateError(f"Appointment already {appt['status']}")
    if appt['status'] == 'InProgress' and role != 'admin':
        raise AuthError("Only admin can cancel an in-progress appointment")

    hours_until = (appt['appt_datetime'] - datetime.now()).total_seconds() / 3600
    # BUG (intentional): late cancellation flag not set for admin cancellations
    # Students should find this in HW1 state testing
    if cancelled_by != 'admin' and hours_until < LATE_CANCEL_HOURS:
        appt['is_late_cancellation'] = True

    appt['status'] = 'Cancelled'
    appt['cancellation_reason'] = reason
    appt['cancelled_by'] = cancelled_by
    appt['cancelled_at'] = datetime.now()


def check_in(appt_id: str, checked_in_by: str) -> None:
    appt = _appointments.get(appt_id)
    if appt is None:
        raise ValidationError("Appointment not found")
    if appt['status'] != 'Scheduled':
        raise InvalidStateError(f"Cannot check in — status is {appt['status']}")
    appt['status'] = 'CheckedIn'
    appt['checked_in_by'] = checked_in_by
    appt['checked_in_at'] = datetime.now()


def start_visit(appt_id: str) -> None:
    appt = _appointments.get(appt_id)
    if appt is None:
        raise ValidationError("Appointment not found")
    if appt['status'] != 'CheckedIn':
        raise InvalidStateError("Must check in before starting visit")
    appt['status'] = 'InProgress'


def complete_appointment(appt_id: str, notes: str, provider_id: str) -> None:
    appt = _appointments.get(appt_id)
    if appt is None:
        raise ValidationError("Appointment not found")
    if appt['status'] != 'InProgress':
        raise InvalidStateError("Appointment must be InProgress to complete")
    if appt['provider_id'] != provider_id:
        raise AuthError("Not the treating provider")
    if not notes or len(notes.strip()) == 0:
        raise ValidationError("Completion notes are required")
    appt['status'] = 'Completed'
    appt['completion_notes'] = notes
    appt['completed_at'] = datetime.now()


def get_appointment(appt_id: str) -> dict:
    return _appointments.get(appt_id)


def reschedule_appointment(appt_id: str, new_dt: datetime, requesting_user) -> str:
    appt = _appointments.get(appt_id)
    if appt is None:
        raise ValidationError("Appointment not found")
    if appt['status'] != 'Cancelled':
        raise InvalidStateError("Only Cancelled appointments can be rescheduled")
    if new_dt <= datetime.now():
        raise ValidationError("New appointment time must be in the future")
    if requesting_user.role not in ('admin', 'receptionist'):
        raise AuthError("Insufficient role — admin or receptionist required")

    new_id = schedule_appointment(
        appt['patient_id'], appt['provider_id'],
        new_dt, appt['appt_type'], appt['duration_minutes']
    )
    return new_id
