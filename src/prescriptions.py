"""MediTrack — Module 3: Prescription Management.

Path-testing target for HW2.
  add_prescription() has four decision nodes → V(G) = 5
  Basis paths P1–P5 are documented in the course path-testing notes.
"""
import uuid
from datetime import datetime, date
from config import (VALID_FREQUENCIES, MIN_DAYS_SUPPLY, MAX_DAYS_SUPPLY)
from exceptions import ValidationError, AuthError, InvalidStateError

_prescriptions = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_medication_name(name: str) -> None:
    if not name or not isinstance(name, str) or not name.strip():
        raise ValidationError("medication_name must be a non-empty string")
    if len(name.strip()) > 200:
        raise ValidationError("medication_name must be ≤ 200 characters")


def _validate_dosage(dosage: str) -> None:
    if not dosage or not isinstance(dosage, str) or not dosage.strip():
        raise ValidationError("dosage must be a non-empty string (e.g. '10mg')")
    if len(dosage.strip()) > 100:
        raise ValidationError("dosage must be ≤ 100 characters")


# ---------------------------------------------------------------------------
# Core function — primary path-testing target
# ---------------------------------------------------------------------------

def add_prescription(patient_id: str, provider_id: str,
                     medication_name: str, dosage: str,
                     frequency: str, days_supply: int,
                     notes: str = None) -> str:
    """Create a new prescription record. Returns prescription_id.

    Decision nodes (basis for HW2 path testing, V(G) = 5):
        D1: frequency not in VALID_FREQUENCIES
        D2: days_supply < MIN_DAYS_SUPPLY or days_supply > MAX_DAYS_SUPPLY
        D3: patient has an existing active prescription for the same medication
        D4: notes provided and len(notes) > 500

    Basis paths:
        P1 (happy path)   — D1=F, D2=F, D3=F, D4=F → prescription created, no warning
        P2 (bad freq)     — D1=T                   → ValidationError raised
        P3 (bad supply)   — D1=F, D2=T             → ValidationError raised
        P4 (duplicate Rx) — D1=F, D2=F, D3=T       → duplicate_warning set, still created
        P5 (long notes)   — D1=F, D2=F, D3=F, D4=T → ValidationError raised

    Args:
        patient_id:       UUID of the patient (must exist in patients store).
        provider_id:      UUID or identifier of the prescribing provider.
        medication_name:  Free-text drug name (e.g. 'Metformin').
        dosage:           Strength/form string (e.g. '500mg tablet').
        frequency:        Must be one of config.VALID_FREQUENCIES.
        days_supply:      Integer in [MIN_DAYS_SUPPLY, MAX_DAYS_SUPPLY].
        notes:            Optional free-text instructions; max 500 characters.

    Returns:
        prescription_id (UUID string)

    Raises:
        ValidationError:  Invalid inputs or duplicate-Rx attempt.
        AuthError:        (reserved for future role checks on provider_id).
    """
    from patients import get_patient

    # Validate patient exists
    if get_patient(patient_id) is None:
        raise ValidationError(f"Patient {patient_id} not found")

    _validate_medication_name(medication_name)
    _validate_dosage(dosage)

    # D1 — frequency check
    if frequency not in VALID_FREQUENCIES:
        raise ValidationError(
            f"Invalid frequency '{frequency}'. Valid: {VALID_FREQUENCIES}"
        )

    # D2 — days_supply range check
    if not isinstance(days_supply, int) or \
            days_supply < MIN_DAYS_SUPPLY or days_supply > MAX_DAYS_SUPPLY:
        raise ValidationError(
            f"days_supply must be an integer in "
            f"[{MIN_DAYS_SUPPLY}, {MAX_DAYS_SUPPLY}], got {days_supply!r}"
        )

    # D3 — duplicate active prescription check (warning, not hard block)
    duplicate_warning = None
    med_lower = medication_name.strip().lower()
    for rx in _prescriptions.values():
        if (rx['patient_id'] == patient_id
                and rx['medication_name'].lower() == med_lower
                and rx['status'] == 'Active'):
            duplicate_warning = (
                f"Patient already has an active prescription for "
                f"'{medication_name}' (rx_id={rx['prescription_id']})"
            )
            break

    # D4 — notes length check
    if notes is not None and len(notes) > 500:
        raise ValidationError("notes must be ≤ 500 characters")

    rx_id = str(uuid.uuid4())
    _prescriptions[rx_id] = {
        'prescription_id': rx_id,
        'patient_id': patient_id,
        'provider_id': provider_id,
        'medication_name': medication_name.strip(),
        'dosage': dosage.strip(),
        'frequency': frequency,
        'days_supply': days_supply,
        'notes': notes,
        'status': 'Active',
        'duplicate_warning': duplicate_warning,
        'prescribed_at': datetime.now(),
        'filled_at': None,
        'discontinued_at': None,
        'discontinued_reason': None,
    }
    return rx_id


# ---------------------------------------------------------------------------
# Supporting operations
# ---------------------------------------------------------------------------

def get_prescription(prescription_id: str) -> dict:
    """Return prescription record or None if not found."""
    return _prescriptions.get(prescription_id)


def list_prescriptions(patient_id: str, active_only: bool = False) -> list:
    """Return all prescriptions for a patient.

    Args:
        patient_id:   UUID of the patient.
        active_only:  If True, return only records with status='Active'.

    Returns:
        List of prescription dicts (copies), may be empty.
    """
    results = []
    for rx in _prescriptions.values():
        if rx['patient_id'] != patient_id:
            continue
        if active_only and rx['status'] != 'Active':
            continue
        results.append(dict(rx))
    return results


def fill_prescription(prescription_id: str) -> None:
    """Mark a prescription as filled (status: Active → Filled).

    Raises:
        ValidationError:  Prescription not found.
        InvalidStateError: Prescription is not in Active status.
    """
    rx = _prescriptions.get(prescription_id)
    if rx is None:
        raise ValidationError(f"Prescription {prescription_id} not found")
    if rx['status'] != 'Active':
        raise InvalidStateError(
            f"Cannot fill — prescription status is '{rx['status']}'"
        )
    rx['status'] = 'Filled'
    rx['filled_at'] = datetime.now()


def discontinue_prescription(prescription_id: str, reason: str,
                              requesting_user) -> None:
    """Discontinue a prescription. Requires admin or provider role.

    Args:
        prescription_id:  UUID of the prescription.
        reason:           Free-text reason (required, non-empty).
        requesting_user:  User object; must have role 'admin' or 'provider'.

    Raises:
        ValidationError:  Prescription not found or missing reason.
        AuthError:        Insufficient role.
        InvalidStateError: Prescription already discontinued.
    """
    rx = _prescriptions.get(prescription_id)
    if rx is None:
        raise ValidationError(f"Prescription {prescription_id} not found")

    requesting_user.require_role('admin', 'provider')

    if rx['status'] == 'Discontinued':
        raise InvalidStateError("Prescription is already discontinued")
    if not reason or not reason.strip():
        raise ValidationError("Discontinuation reason is required")

    rx['status'] = 'Discontinued'
    rx['discontinued_at'] = datetime.now()
    rx['discontinued_reason'] = reason.strip()
