import pytest
from unittest.mock import MagicMock, patch

from billing_additions import create_invoice


def test_path_1_missing_patient_id():
    """Path 1: patient_id is None"""
    with pytest.raises(ValueError):
        create_invoice(None, 1, 100.00, "Pending")


def test_path_2_invalid_appointment_id():
    """Path 2: appointment_id is invalid"""
    with pytest.raises(ValueError):
        create_invoice(1, 0, 100.00, "Pending")


def test_path_3_invalid_amount():
    """Path 3: amount is None or amount <= 0"""
    with pytest.raises(ValueError):
        create_invoice(1, 1, 0, "Pending")


def test_path_4_invalid_status():
    """Path 4: status is not valid"""
    with pytest.raises(ValueError):
        create_invoice(1, 1, 100.00, "BadStatus")


@patch("billing_additions.get_connection")
def test_path_5_valid_invoice_created(mock_get_connection):
    """Path 5: all inputs valid and invoice is created"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.lastrowid = 10

    mock_conn.cursor.return_value = mock_cursor
    mock_get_connection.return_value = mock_conn

    result = create_invoice(1, 1, 100.00, "Pending", "regular visit")

    assert result == 10
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()