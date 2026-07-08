"""MediTrack — Module 4: Medical Records.

Integration-testing target for HW3.
  Depends on: patients (Module 1), appointments (Module 2)
  Required by: billing (Module 5)

Key constraint: a record can only be created for a Completed appointment,
enforcing the DAG: patients → appointments → records → billing.
"""
import uuid
import re
from datetime import datetime
from config import (ICD_PATTERN, MIN_CHIEF_COMPLAINT, MAX_CHIEF_COMPLAINT)
from exceptions import ValidationError, AuthError, InvalidStateError

_records = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_icd_code(code: str) -> None:
    """Validate ICD-10 format: letter + 2 digits + optional .1–4 alphanum."""
    if not code or not isinstance(code, str):
        raise ValidationError("icd_code must be a non-empty string")
    if not ICD_PATTERN.match(code.strip().upper()):
        raise ValidationError(
            f"icd_code '{code}' does not match ICD-10 format "
            f"(e.g. 'A01', 'E11.9', 'Z00.00')"
        )


def _validate_chief_complaint(complaint: str) -> None:
    if not complaint or not isinstance(complaint, str):
        raise ValidationError("chief_complaint must be a non-empty string")
    text = complaint.strip()
    if len(text) < MIN_CHIEF_COMPLAINT or len(text) > MAX_CHIEF_COMPLAINT:
        raise ValidationError(
            f"chief_complaint must be {MIN_CHIEF_COMPLAINT}–"
            f"{MAX_CHIEF_COMPLAINT} characters, got {len(text)}"
        )


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def add_record(appointment_id: str, provider_id: str,
               chief_complaint: str, icd_code: str,
               clinical_notes: str, requesting_user) -> str:
    """Create a medical record for a completed appointment.

    The appointment must have status='Completed' — this enforces the
    module dependency: appointments must be completed before records are written.

    Args:
        appointment_id:  UUID of the (Completed) appointment.
        provider_id:     UUID of the treating provider; must match appointment.
        chief_complaint: Patient's primary reason for visit (1–500 chars).
        icd_code:        ICD-10 diagnosis code (e.g. 'E11.9').
        clinical_notes:  Provider's clinical notes (required, non-empty).
        requesting_user: User object; must have role 'admin' or 'provider'.

    Returns:
        record_id (UUID string)

    Raises:
        ValidationError:   Invalid inputs or appointment not found.
        InvalidStateError: Appointment is not Completed.
        AuthError:         Caller lacks required role or is not the treating provider.
    """
    from appointments import get_appointment

    requesting_user.require_role('admin', 'provider')

    appt = get_appointment(appointment_id)
    if appt is None:
        raise ValidationError(f"Appointment {appointment_id} not found")
    if appt['status'] != 'Completed':
        raise InvalidStateError(
            f"Records can only be added to Completed appointments "
            f"(current status: '{appt['status']}')"
        )
    if appt['provider_id'] != provider_id and requesting_user.role != 'admin':
        raise AuthError(
            "Only the treating provider or an admin may create this record"
        )

    _validate_chief_complaint(chief_complaint)
    _validate_icd_code(icd_code)

    if not clinical_notes or not clinical_notes.strip():
        raise ValidationError("clinical_notes are required")

    # Prevent duplicate records for the same appointment
    for rec in _records.values():
        if rec['appointment_id'] == appointment_id:
            raise ValidationError(
                f"A record already exists for appointment {appointment_id} "
                f"(record_id={rec['record_id']})"
            )

    record_id = str(uuid.uuid4())
    _records[record_id] = {
        'record_id': record_id,
        'appointment_id': appointment_id,
        'patient_id': appt['patient_id'],
        'provider_id': provider_id,
        'chief_complaint': chief_complaint.strip(),
        'icd_code': icd_code.strip().upper(),
        'clinical_notes': clinical_notes.strip(),
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
    }
    return record_id


def get_record(record_id: str) -> dict:
    """Return a record dict by ID, or None if not found."""
    return _records.get(record_id)


def get_record_for_appointment(appointment_id: str) -> dict:
    """Return the record associated with a given appointment, or None."""
    for rec in _records.values():
        if rec['appointment_id'] == appointment_id:
            return dict(rec)
    return None


def get_patient_records(patient_id: str) -> list:
    """Return all records for a patient, sorted newest-first.

    Args:
        patient_id: UUID of the patient.

    Returns:
        List of record dicts (copies). May be empty.
    """
    results = [
        dict(rec) for rec in _records.values()
        if rec['patient_id'] == patient_id
    ]
    return sorted(results, key=lambda r: r['created_at'], reverse=True)


def update_record(record_id: str, clinical_notes: str,
                  icd_code: str = None, requesting_user=None) -> None:
    """Amend clinical notes and/or ICD code on an existing record.

    Args:
        record_id:       UUID of the record to update.
        clinical_notes:  New clinical notes (required, non-empty).
        icd_code:        New ICD-10 code (optional; leave None to keep current).
        requesting_user: User object; must have role 'admin' or 'provider'.

    Raises:
        ValidationError: Record not found or invalid inputs.
        AuthError:       Insufficient role.
    """
    if requesting_user is not None:
        requesting_user.require_role('admin', 'provider')

    rec = _records.get(record_id)
    if rec is None:
        raise ValidationError(f"Record {record_id} not found")
    if not clinical_notes or not clinical_notes.strip():
        raise ValidationError("clinical_notes must be a non-empty string")
    if icd_code is not None:
        _validate_icd_code(icd_code)
        rec['icd_code'] = icd_code.strip().upper()

    rec['clinical_notes'] = clinical_notes.strip()
    rec['updated_at'] = datetime.now()
