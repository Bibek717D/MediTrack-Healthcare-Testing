"""MediTrack — Module 1: Patient Registration."""
import re
import uuid
from datetime import date, datetime
from config import (MAX_NAME_LENGTH, MIN_NAME_LENGTH, PHONE_LENGTH,
                    MAX_EMAIL_LENGTH, MIN_INSURANCE_ID_LENGTH, MAX_INSURANCE_ID_LENGTH)
from exceptions import ValidationError

# In-memory store for testing (replaced by real DB in production)
_patients = {}


def _validate_name(name: str, field: str) -> None:
    if not name or not isinstance(name, str):
        raise ValidationError(f"{field} must be a non-empty string")
    if len(name) < MIN_NAME_LENGTH or len(name) > MAX_NAME_LENGTH:
        raise ValidationError(
            f"{field} must be {MIN_NAME_LENGTH}–{MAX_NAME_LENGTH} chars, got {len(name)}")
    if not re.match(r"^[A-Za-z\-]+$", name):
        raise ValidationError(f"{field} must contain only letters and hyphens")


def _validate_phone(phone: str) -> None:
    if not phone or not isinstance(phone, str):
        raise ValidationError("Phone must be a string")
    digits = re.sub(r"\D", "", phone)
    if len(digits) != PHONE_LENGTH:
        raise ValidationError(f"Phone must be exactly {PHONE_LENGTH} digits, got {len(digits)}")


def _validate_email(email: str) -> None:
    if not email or len(email) > MAX_EMAIL_LENGTH:
        raise ValidationError("Email must be non-empty and ≤100 characters")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValidationError(f"Invalid email format: {email}")


def _validate_dob(dob: date) -> None:
    if not isinstance(dob, date):
        raise ValidationError("date_of_birth must be a date object")
    today = date.today()
    if dob > today:
        raise ValidationError("date_of_birth cannot be in the future")
    age_years = (today - dob).days / 365.25
    if age_years > 130:
        raise ValidationError("date_of_birth too far in the past (> 130 years)")


def register_patient(first_name: str, last_name: str, dob: date,
                     phone: str, email: str, insurance_id: str = None) -> str:
    """Register a new patient. Returns the generated patient_id (UUID).

    Raises ValidationError for any invalid input.
    """
    _validate_name(first_name, "first_name")
    _validate_name(last_name, "last_name")
    _validate_dob(dob)
    _validate_phone(phone)
    _validate_email(email)

    if insurance_id is not None:
        ins = str(insurance_id).strip()
        if not ins.isalnum():
            raise ValidationError("insurance_id must be alphanumeric")
        if len(ins) < MIN_INSURANCE_ID_LENGTH or len(ins) > MAX_INSURANCE_ID_LENGTH:
            raise ValidationError(
                f"insurance_id must be {MIN_INSURANCE_ID_LENGTH}–{MAX_INSURANCE_ID_LENGTH} chars")

    # Duplicate detection (warning — not a hard block)
    duplicate_warning = None
    for pid, p in _patients.items():
        if (p['first_name'].lower() == first_name.lower() and
                p['last_name'].lower() == last_name.lower() and
                p['dob'] == dob):
            duplicate_warning = f"Possible duplicate of patient {pid}"
            break

    patient_id = str(uuid.uuid4())
    _patients[patient_id] = {
        'patient_id': patient_id,
        'first_name': first_name,
        'last_name': last_name,
        'dob': dob,
        'phone': re.sub(r"\D", "", phone),
        'email': email,
        'insurance_id': insurance_id,
        'is_active': True,
        'created_at': datetime.now(),
        'duplicate_warning': duplicate_warning,
    }
    return patient_id


def get_patient(patient_id: str) -> dict:
    """Retrieve a patient record by ID. Returns None if not found."""
    return _patients.get(patient_id)


def search_patients(query: str, field: str = 'name') -> list:
    """Search patients by name or ID. Sanitizes query to prevent injection."""
    if not query or not isinstance(query, str):
        return []
    # Sanitize: strip SQL-special characters
    safe_query = re.sub(r"[\';\-\-]", "", query).strip().lower()
    results = []
    for p in _patients.values():
        if not p['is_active']:
            continue
        if field == 'name':
            full_name = f"{p['first_name']} {p['last_name']}".lower()
            if safe_query in full_name:
                results.append(dict(p))
        elif field == 'id' and safe_query == p['patient_id'].lower():
            results.append(dict(p))
    return results


def deactivate_patient(patient_id: str, reason: str, requesting_user) -> None:
    """Deactivate a patient record. Requires admin or provider role."""
    patient = _patients.get(patient_id)
    if patient is None:
        raise ValidationError(f"Patient {patient_id} not found")
    if requesting_user.role not in ('admin', 'provider'):
        raise AuthError("Insufficient permissions — admin or provider required")
    if not reason or len(reason.strip()) == 0:
        raise ValidationError("Deactivation reason is required")
    patient['is_active'] = False
    patient['deactivation_reason'] = reason
    patient['deactivated_at'] = datetime.now()
