"""MediTrack — Module 5: Billing & Invoicing.

End of the dependency DAG: patients → appointments → records → billing.
An invoice can only be created once a medical record exists for the appointment.

Combinatorial-testing target for HW5:
  process_payment() has three independent configuration parameters
  (payment_method × insurance_applied × partial_payment),
  making it suitable for pairwise / all-pairs testing.
"""
import uuid
from datetime import datetime
from config import (VALID_PAYMENT_METHODS, INVOICE_STATES)
from exceptions import (ValidationError, AuthError, InvalidStateError,
                        DuplicateInvoiceError, InsuranceNotFoundError)

_invoices = {}

# Simulated insurance plan registry (stub — replaced by real DB in production)
_insurance_registry = {
    'INS001': {'plan_name': 'BlueCross Basic',   'coverage_pct': 0.80},
    'INS002': {'plan_name': 'Aetna Plus',        'coverage_pct': 0.90},
    'INS003': {'plan_name': 'United Health PPO', 'coverage_pct': 0.70},
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_record_for_appointment(appointment_id: str) -> dict:
    """Raise ValidationError unless a medical record exists for this appointment."""
    from records import get_record_for_appointment
    rec = get_record_for_appointment(appointment_id)
    if rec is None:
        raise ValidationError(
            f"No medical record found for appointment {appointment_id}. "
            f"A record must be created before billing."
        )
    return rec


def _get_invoice_by_appointment(appointment_id: str) -> dict:
    for inv in _invoices.values():
        if inv['appointment_id'] == appointment_id:
            return inv
    return None


# ---------------------------------------------------------------------------
# Invoice lifecycle
# ---------------------------------------------------------------------------

def create_invoice(appointment_id: str, line_items: list,
                   requesting_user) -> str:
    """Create a Draft invoice for a completed, recorded appointment.

    Args:
        appointment_id:  UUID of the appointment (must have a medical record).
        line_items:      Non-empty list of dicts, each with:
                           - 'description' (str, required)
                           - 'amount'      (float > 0, required)
        requesting_user: User object; must have role 'admin' or 'receptionist'.

    Returns:
        invoice_id (UUID string)

    Raises:
        ValidationError:      Invalid inputs or no record for the appointment.
        DuplicateInvoiceError: Invoice already exists for this appointment.
        AuthError:            Insufficient role.
    """
    requesting_user.require_role('admin', 'receptionist')

    _require_record_for_appointment(appointment_id)

    if _get_invoice_by_appointment(appointment_id) is not None:
        raise DuplicateInvoiceError(
            f"An invoice already exists for appointment {appointment_id}"
        )

    if not line_items or not isinstance(line_items, list):
        raise ValidationError("line_items must be a non-empty list")

    validated_items = []
    total = 0.0
    for i, item in enumerate(line_items):
        if not isinstance(item, dict):
            raise ValidationError(f"line_items[{i}] must be a dict")
        desc = item.get('description', '')
        amt = item.get('amount')
        if not desc or not str(desc).strip():
            raise ValidationError(f"line_items[{i}] missing 'description'")
        if not isinstance(amt, (int, float)) or amt <= 0:
            raise ValidationError(
                f"line_items[{i}]['amount'] must be a positive number, got {amt!r}"
            )
        validated_items.append({'description': str(desc).strip(), 'amount': float(amt)})
        total += float(amt)

    invoice_id = str(uuid.uuid4())
    _invoices[invoice_id] = {
        'invoice_id': invoice_id,
        'appointment_id': appointment_id,
        'line_items': validated_items,
        'total_amount': round(total, 2),
        'amount_paid': 0.0,
        'balance_due': round(total, 2),
        'status': 'Draft',
        'insurance_applied': False,
        'insurance_id': None,
        'insurance_coverage_pct': None,
        'insurance_covered_amount': 0.0,
        'payments': [],
        'created_at': datetime.now(),
        'submitted_at': None,
        'voided_at': None,
        'voided_reason': None,
    }
    return invoice_id


def submit_invoice(invoice_id: str) -> None:
    """Transition invoice from Draft → Submitted.

    Raises:
        ValidationError:   Invoice not found.
        InvalidStateError: Invoice not in Draft status.
    """
    inv = _invoices.get(invoice_id)
    if inv is None:
        raise ValidationError(f"Invoice {invoice_id} not found")
    if inv['status'] != 'Draft':
        raise InvalidStateError(
            f"Only Draft invoices can be submitted (current: '{inv['status']}')"
        )
    inv['status'] = 'Submitted'
    inv['submitted_at'] = datetime.now()


def apply_insurance(invoice_id: str, insurance_id: str) -> float:
    """Apply insurance coverage to a Submitted invoice.

    Looks up the insurance plan in the registry and reduces balance_due
    by the plan's coverage percentage. Sets insurance_applied = True.

    Args:
        invoice_id:   UUID of the invoice (must be Submitted).
        insurance_id: Key into the insurance registry (e.g. 'INS001').

    Returns:
        covered_amount (float) — the portion covered by insurance.

    Raises:
        ValidationError:      Invoice not found or insurance already applied.
        InvalidStateError:    Invoice not in Submitted status.
        InsuranceNotFoundError: insurance_id not in registry.
    """
    inv = _invoices.get(invoice_id)
    if inv is None:
        raise ValidationError(f"Invoice {invoice_id} not found")
    if inv['status'] != 'Submitted':
        raise InvalidStateError(
            f"Insurance can only be applied to Submitted invoices "
            f"(current: '{inv['status']}')"
        )
    if inv['insurance_applied']:
        raise ValidationError("Insurance has already been applied to this invoice")

    plan = _insurance_registry.get(insurance_id)
    if plan is None:
        raise InsuranceNotFoundError(
            f"Insurance plan '{insurance_id}' not found in registry"
        )

    coverage_pct = plan['coverage_pct']
    covered = round(inv['total_amount'] * coverage_pct, 2)

    inv['insurance_applied'] = True
    inv['insurance_id'] = insurance_id
    inv['insurance_coverage_pct'] = coverage_pct
    inv['insurance_covered_amount'] = covered
    inv['balance_due'] = round(inv['total_amount'] - covered, 2)
    return covered


def process_payment(invoice_id: str, amount: float,
                    payment_method: str, notes: str = None) -> None:
    """Record a patient payment against a Submitted or PartiallyPaid invoice.

    Combinatorial-testing target (HW5 — pairwise / all-pairs):
      Parameters of interest:
        payment_method  — one of VALID_PAYMENT_METHODS (5 values)
        amount          — exact balance_due (full) vs partial (< balance_due)
        insurance       — whether apply_insurance() was called first

      All-pairs requires covering every combination of these three factors.

    Args:
        invoice_id:     UUID of the invoice.
        amount:         Payment amount (> 0, ≤ balance_due).
        payment_method: Must be one of config.VALID_PAYMENT_METHODS.
        notes:          Optional free-text payment reference.

    Raises:
        ValidationError:   Invoice not found, invalid amount, invalid method.
        InvalidStateError: Invoice not in a payable state (Submitted / PartiallyPaid).
    """
    inv = _invoices.get(invoice_id)
    if inv is None:
        raise ValidationError(f"Invoice {invoice_id} not found")
    if inv['status'] not in ('Submitted', 'PartiallyPaid'):
        raise InvalidStateError(
            f"Payment can only be applied to Submitted or PartiallyPaid invoices "
            f"(current: '{inv['status']}')"
        )
    if payment_method not in VALID_PAYMENT_METHODS:
        raise ValidationError(
            f"Invalid payment_method '{payment_method}'. "
            f"Valid: {VALID_PAYMENT_METHODS}"
        )
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValidationError(f"amount must be a positive number, got {amount!r}")
    if round(amount, 2) > round(inv['balance_due'], 2):
        raise ValidationError(
            f"Payment amount {amount:.2f} exceeds balance due "
            f"{inv['balance_due']:.2f}"
        )

    inv['payments'].append({
        'amount': round(amount, 2),
        'payment_method': payment_method,
        'notes': notes,
        'paid_at': datetime.now(),
    })
    inv['amount_paid'] = round(inv['amount_paid'] + amount, 2)
    inv['balance_due'] = round(inv['balance_due'] - amount, 2)

    if inv['balance_due'] <= 0:
        inv['status'] = 'Paid'
    else:
        inv['status'] = 'PartiallyPaid'


def void_invoice(invoice_id: str, reason: str, requesting_user) -> None:
    """Void an invoice. Only admin may void.

    Args:
        invoice_id:      UUID of the invoice.
        reason:          Required non-empty reason.
        requesting_user: User object; must have role 'admin'.

    Raises:
        ValidationError:   Invoice not found or missing reason.
        AuthError:         Only admin may void invoices.
        InvalidStateError: Cannot void a Paid invoice.
    """
    inv = _invoices.get(invoice_id)
    if inv is None:
        raise ValidationError(f"Invoice {invoice_id} not found")
    requesting_user.require_role('admin')
    if inv['status'] == 'Paid':
        raise InvalidStateError("Cannot void a fully paid invoice")
    if not reason or not reason.strip():
        raise ValidationError("Void reason is required")

    inv['status'] = 'Voided'
    inv['voided_at'] = datetime.now()
    inv['voided_reason'] = reason.strip()


def get_invoice(invoice_id: str) -> dict:
    """Return invoice dict by ID, or None."""
    return _invoices.get(invoice_id)


def get_invoice_for_appointment(appointment_id: str) -> dict:
    """Return the invoice for a given appointment, or None."""
    inv = _get_invoice_by_appointment(appointment_id)
    return dict(inv) if inv else None
