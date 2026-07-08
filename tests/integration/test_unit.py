import pytest
from unittest.mock import MagicMock, patch

import billing
import records

def test_tc_ci_1_valid_appointment_returns_invoice_id():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.lastrowid = 101
    mock_conn.cursor.return_value = mock_cursor

    with patch("billing.get_db_connection", return_value=mock_conn):
        invoice_id = billing.create_invoice(
            patient_id=1,
            appointment_id=1,
            amount=200.00,
            status="Pending",
            notes="Office Visit"
        )

    assert invoice_id == 101

    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

def test_tc_ci_2_appointment_not_found():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.execute.side_effect = ValueError("Appointment not found")
    mock_conn.cursor.return_value = mock_cursor

    with patch("billing.get_db_connection", return_value=mock_conn):
        with pytest.raises(ValueError, match="Appointment not found"):
            billing.create_invoice(
                patient_id=1,
                appointment_id=999,
                amount=200.00,
                status="Pending"
            )

def test_tc_ci_3_no_services_provided():
    with pytest.raises(ValueError, match="Invoice amount must be greater than zero"):
        billing.create_invoice(
            patient_id=1,
            appointment_id=1,
            amount=0,
            status="Pending"
        )

def test_tc_ci_4_duplicate_invoice():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.execute.side_effect = Exception("DuplicateInvoiceError")
    mock_conn.cursor.return_value = mock_cursor

    with patch("billing.get_db_connection", return_value=mock_conn):
        with pytest.raises(Exception, match="DuplicateInvoiceError"):
            billing.create_invoice(
                patient_id=1,
                appointment_id=1,
                amount=200.00,
                status="Pending"
            )

def test_tc_ai_1_valid_insurance():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchone.return_value = (
        200.0,          # original amount
        "Pending",      # status
        0,              # insurance_applied
        None,
        None
    )

    mock_conn.cursor.return_value = mock_cursor

    with patch("billing.get_db_connection", return_value=mock_conn):
        result = billing.apply_insurance(
            invoice_id=1,
            insurance_provider="BlueCross",
            coverage_pct=80
        )

    assert result["insurance_applied"] is True
    assert result["coverage_pct"] == 80
    assert result["balance_due"] == 40.0
    assert result["insurance_covers"] == 160.0

    mock_conn.commit.assert_called_once()

def test_tc_ai_2_insurance_not_found():
    with pytest.raises(ValueError, match="Unsupported insurance provider"):
        billing.apply_insurance(
            invoice_id=1,
            insurance_provider="UnknownInsurance",
            coverage_pct=80
        )

def test_tc_ai_3_self_pay_balance_unchanged():
    result = billing.apply_insurance(
        invoice_id=1,
        insurance_provider=None,
        coverage_pct=0
    )

    assert result["insurance_applied"] is False
    assert result["coverage_pct"] == 0.0
    assert result["insurance_covers"] == 0.0
    assert result["balance_due"] is None

def test_tc_ai_4_insurance_already_applied():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchone.return_value = (
        200.0,     # original amount
        "Pending", # status
        1,         # insurance already applied
        80.0,      # previous coverage %
        40.0       # previous balance
    )

    mock_conn.cursor.return_value = mock_cursor

    with patch("billing.get_db_connection", return_value=mock_conn):
        result = billing.apply_insurance(
            invoice_id=1,
            insurance_provider="BlueCross",
            coverage_pct=50
        )

    assert result["insurance_applied"] is True
    assert result["coverage_pct"] == 80.0
    assert result["balance_due"] == 40.0
    assert result["insurance_covers"] == 160.0

    mock_conn.commit.assert_not_called()


def test_tc_rx_1_valid_diagnosis_returns_record_id():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchone.side_effect = [
        {"patient_id": 1, "is_active": 1},
        {"appointment_id": 1, "patient_id": 1, "status": "checked_in"},
        None
    ]
    mock_cursor.lastrowid = 501
    mock_conn.cursor.return_value = mock_cursor

    with patch("records.get_connection", return_value=mock_conn):
        result = records.add_diagnosis(
            patient_id=1,
            appointment_id=1,
            diagnosis="Chest pain",
            notes="Patient reports chest discomfort",
            prescriptions="aspirin"
        )

    assert result["record_id"] == 501
    assert result["action"] == "inserted"
    assert result["diagnosis"] == "Chest pain"
    mock_conn.commit.assert_called_once()

def test_tc_rx_2_empty_diagnosis_validation_error():
    with pytest.raises(ValueError, match="diagnosis must be a non-empty string"):
        records.add_diagnosis(
            patient_id=1,
            appointment_id=1,
            diagnosis="",
            notes="test",
            prescriptions="aspirin"
        )

def test_tc_rx_3_whitespace_diagnosis_validation_error():
    with pytest.raises(ValueError, match="diagnosis must be a non-empty string"):
        records.add_diagnosis(
            patient_id=1,
            appointment_id=1,
            diagnosis="   ",
            notes="test",
            prescriptions="ibuprofen"
        )

def test_tc_rx_4_inactive_patient():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Patient exists but is inactive
    mock_cursor.fetchone.return_value = {
        "patient_id": 1,
        "is_active": 0
    }

    mock_conn.cursor.return_value = mock_cursor

    with patch("records.get_connection", return_value=mock_conn):
        with pytest.raises(
            ValueError,
            match="Patient 1 is inactive and cannot receive a diagnosis."
        ):
            records.add_diagnosis(
                patient_id=1,
                appointment_id=1,
                diagnosis="Chest pain"
            )

def test_tc_rx_5_appointment_not_found():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchone.side_effect = [
        {"patient_id": 1, "is_active": 1},  # patient exists
        None                               # appointment not found
    ]

    mock_conn.cursor.return_value = mock_cursor

    with patch("records.get_connection", return_value=mock_conn):
        with pytest.raises(
            ValueError,
            match="Appointment 999 does not exist."
        ):
            records.add_diagnosis(
                patient_id=1,
                appointment_id=999,
                diagnosis="Chest pain"
            )

def test_tc_rx_6_appointment_wrong_patient():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchone.side_effect = [
        {"patient_id": 1, "is_active": 1},
        {"appointment_id": 10, "patient_id": 2, "status": "checked_in"}
    ]

    mock_conn.cursor.return_value = mock_cursor

    with patch("records.get_connection", return_value=mock_conn):
        with pytest.raises(
            ValueError,
            match="Appointment 10 does not belong to patient 1."
        ):
            records.add_diagnosis(
                patient_id=1,
                appointment_id=10,
                diagnosis="Chest pain"
            )
def test_tc_rx_7_invalid_appointment_status():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchone.side_effect = [
        {"patient_id": 1, "is_active": 1},
        {"appointment_id": 10, "patient_id": 1, "status": "scheduled"}
    ]

    mock_conn.cursor.return_value = mock_cursor

    with patch("records.get_connection", return_value=mock_conn):
        with pytest.raises(ValueError, match="Cannot add diagnosis"):
            records.add_diagnosis(
                patient_id=1,
                appointment_id=10,
                diagnosis="Chest pain"
            )

def test_tc_rx_8_existing_record_updates():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchone.side_effect = [
        {"patient_id": 1, "is_active": 1},
        {"appointment_id": 10, "patient_id": 1, "status": "completed"},
        {"record_id": 777}
    ]

    mock_conn.cursor.return_value = mock_cursor

    with patch("records.get_connection", return_value=mock_conn):
        result = records.add_diagnosis(
            patient_id=1,
            appointment_id=10,
            diagnosis="Updated diagnosis",
            notes="Updated notes",
            prescriptions="aspirin"
        )

    assert result["record_id"] == 777
    assert result["action"] == "updated"
    assert result["diagnosis"] == "Updated diagnosis"
    mock_conn.commit.assert_called_once()