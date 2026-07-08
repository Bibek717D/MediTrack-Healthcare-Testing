import pytest
from unittest.mock import patch

import billing
from exceptions import (
    ValidationError,
    InvalidStateError,
    InsuranceNotFoundError,
    AuthError,
    DuplicateInvoiceError,
)


def make_invoice(status="Submitted", balance=100.0):
    invoice_id = "inv-001"
    billing._invoices[invoice_id] = {
        "invoice_id": invoice_id,
        "appointment_id": "appt-001",
        "line_items": [],
        "total_amount": balance,
        "amount_paid": 0.0,
        "balance_due": balance,
        "status": status,
        "insurance_applied": False,
        "insurance_id": None,
        "insurance_coverage_pct": None,
        "insurance_covered_amount": 0.0,
        "payments": [],
    }
    return invoice_id


def test_invoice_not_found():
    """SW1 - invoice.status is None/not found."""
    with pytest.raises(ValidationError):
        billing.process_payment("missing", 50, "cash")


def test_invalid_invoice_state():
    """SW2 - invoice.status is Draft."""
    invoice_id = make_invoice(status="Draft")
    with pytest.raises(InvalidStateError):
        billing.process_payment(invoice_id, 50, "cash")


def test_voided_invoice_state():
    """SW3 - invoice.status is Voided."""
    invoice_id = make_invoice(status="Voided")
    with pytest.raises(InvalidStateError):
        billing.process_payment(invoice_id, 50, "cash")


def test_paid_invoice_state():
    """SW4 - invoice.status is Paid."""
    invoice_id = make_invoice(status="Paid")
    with pytest.raises(InvalidStateError):
        billing.process_payment(invoice_id, 50, "cash")


def test_overpayment():
    """SW5 - Submitted invoice with amount greater than balance."""
    invoice_id = make_invoice(status="Submitted", balance=100)
    with pytest.raises(ValidationError):
        billing.process_payment(invoice_id, 150, "cash")


def test_exact_payment():
    """SW6 - Submitted invoice with amount equal to balance."""
    invoice_id = make_invoice(status="Submitted", balance=100)
    billing.process_payment(invoice_id, 100, "cash")
    assert billing.get_invoice(invoice_id)["status"] == "Paid"


def test_partial_payment():
    """SW7 - Submitted invoice with amount less than balance."""
    invoice_id = make_invoice(status="Submitted", balance=100)
    billing.process_payment(invoice_id, 40, "cash")
    assert billing.get_invoice(invoice_id)["status"] == "PartiallyPaid"


def test_partially_paid_exact_payment():
    """SW8 - PartiallyPaid invoice with amount equal to balance."""
    invoice_id = make_invoice(status="PartiallyPaid", balance=60)
    billing.process_payment(invoice_id, 60, "cash")
    assert billing.get_invoice(invoice_id)["status"] == "Paid"


def test_unknown_status():
    """SW9 - invoice.status is unknown_status."""
    invoice_id = make_invoice(status="unknown_status")
    with pytest.raises(InvalidStateError):
        billing.process_payment(invoice_id, 50, "cash")


def test_invalid_payment_method():
    invoice_id = make_invoice()
    with pytest.raises(ValidationError):
        billing.process_payment(invoice_id, 50, "bitcoin")


def test_invalid_amount():
    invoice_id = make_invoice()
    with pytest.raises(ValidationError):
        billing.process_payment(invoice_id, 0, "cash")


def test_submit_missing_invoice():
    with pytest.raises(ValidationError):
        billing.submit_invoice("missing")


def test_submit_wrong_state():
    invoice_id = make_invoice(status="Paid")
    with pytest.raises(InvalidStateError):
        billing.submit_invoice(invoice_id)


def test_apply_insurance_missing_invoice():
    with pytest.raises(ValidationError):
        billing.apply_insurance("missing", "INS001")


def test_apply_insurance_wrong_state():
    invoice_id = make_invoice(status="Draft")
    with pytest.raises(InvalidStateError):
        billing.apply_insurance(invoice_id, "INS001")


def test_apply_insurance_not_found():
    invoice_id = make_invoice(status="Submitted")
    with pytest.raises(InsuranceNotFoundError):
        billing.apply_insurance(invoice_id, "BADINS")


def test_apply_insurance_success():
    invoice_id = make_invoice(status="Submitted", balance=100)
    billing._invoices[invoice_id]["total_amount"] = 100

    covered = billing.apply_insurance(invoice_id, "INS001")

    assert covered == 80
    assert billing.get_invoice(invoice_id)["balance_due"] == 20


def test_apply_insurance_already_applied():
    invoice_id = make_invoice(status="Submitted", balance=100)
    billing._invoices[invoice_id]["insurance_applied"] = True

    with pytest.raises(ValidationError):
        billing.apply_insurance(invoice_id, "INS001")


class User:
    def __init__(self, role):
        self.role = role

    def require_role(self, *roles):
        if self.role not in roles:
            raise AuthError("bad role")


def test_void_invoice_missing():
    with pytest.raises(ValidationError):
        billing.void_invoice("missing", "reason", User("admin"))


def test_void_invoice_paid():
    invoice_id = make_invoice(status="Paid")
    with pytest.raises(InvalidStateError):
        billing.void_invoice(invoice_id, "reason", User("admin"))


def test_void_invoice_missing_reason():
    invoice_id = make_invoice(status="Submitted")
    with pytest.raises(ValidationError):
        billing.void_invoice(invoice_id, "   ", User("admin"))


def test_void_invoice_success():
    invoice_id = make_invoice(status="Submitted")
    billing.void_invoice(invoice_id, "patient request", User("admin"))
    assert billing.get_invoice(invoice_id)["status"] == "Voided"


def test_get_invoice_for_appointment_found():
    invoice_id = make_invoice(status="Submitted")
    result = billing.get_invoice_for_appointment("appt-001")
    assert result["invoice_id"] == invoice_id


def test_get_invoice_for_appointment_not_found():
    result = billing.get_invoice_for_appointment("missing-appt")
    assert result is None


def test_create_invoice_success():
    with patch("billing._require_record_for_appointment", return_value={"id": "rec"}):
        invoice_id = billing.create_invoice(
            "appt-new",
            [{"description": "Visit", "amount": 100}],
            User("admin"),
        )
    assert billing.get_invoice(invoice_id)["status"] == "Draft"


def test_create_invoice_duplicate():
    make_invoice(status="Draft")
    with patch("billing._require_record_for_appointment", return_value={"id": "rec"}):
        with pytest.raises(DuplicateInvoiceError):
            billing.create_invoice(
                "appt-001",
                [{"description": "Visit", "amount": 100}],
                User("admin"),
            )


def test_create_invoice_empty_items():
    with patch("billing._require_record_for_appointment", return_value={"id": "rec"}):
        with pytest.raises(ValidationError):
            billing.create_invoice("appt-new", [], User("admin"))


def test_create_invoice_item_not_dict():
    with patch("billing._require_record_for_appointment", return_value={"id": "rec"}):
        with pytest.raises(ValidationError):
            billing.create_invoice("appt-new", ["bad"], User("admin"))


def test_create_invoice_missing_description():
    with patch("billing._require_record_for_appointment", return_value={"id": "rec"}):
        with pytest.raises(ValidationError):
            billing.create_invoice(
                "appt-new",
                [{"description": "", "amount": 100}],
                User("admin"),
            )


def test_create_invoice_bad_amount():
    with patch("billing._require_record_for_appointment", return_value={"id": "rec"}):
        with pytest.raises(ValidationError):
            billing.create_invoice(
                "appt-new",
                [{"description": "Visit", "amount": 0}],
                User("admin"),
            )