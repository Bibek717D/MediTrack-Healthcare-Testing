import pytest
from unittest.mock import MagicMock, patch


class ValidationError(Exception):
    pass


class AuthError(Exception):
    pass


VALID_FREQUENCIES = {"daily", "weekly", "monthly"}


class Prescription:
    def __init__(self, record_id, medication, dosage, frequency, days_supply):
        self.record_id = record_id
        self.medication = medication
        self.dosage = dosage
        self.frequency = frequency
        self.days_supply = days_supply
        self.id = 101


def add_prescription(record_id, medication, dosage,
                     frequency, days_supply, provider_id):
    record = db.get_record(record_id)          # Node 2
    if record is None:                         # Node 3
        raise ValidationError("Record not found")
    if provider_id != record.provider_id:      # Node 5
        raise AuthError("Wrong provider")
    if days_supply < 1 or days_supply > 365:   # Node 7
        raise ValidationError("days_supply must be 1-365")
    if frequency not in VALID_FREQUENCIES:     # Node 9
        raise ValidationError("Invalid frequency")
    rx = Prescription(record_id, medication, dosage,
                      frequency, days_supply)  # Node 11
    db.save(rx)                                # Node 12
    return rx.id                               # Node 13


db = MagicMock()


def test_du1_record_used_for_none_check():
    """DU1: record defined at N2 and used at N3 to check if record is None."""
    db.get_record.return_value = None

    with pytest.raises(ValidationError):
        add_prescription(1, "Amoxicillin", "500mg", "daily", 10, 99)

    assert db.get_record.return_value is None


def test_du2_record_used_for_provider_check():
    """DU2: record defined at N2 and used at N5 for provider authorization."""
    mock_record = MagicMock()
    mock_record.provider_id = 10
    db.get_record.return_value = mock_record

    with pytest.raises(AuthError):
        add_prescription(1, "Amoxicillin", "500mg", "daily", 10, 99)

    assert db.get_record.return_value.provider_id == 10


def test_du3_record_used_on_successful_path():
    """DU3: record defined at N2 and reaches the successful prescription path."""
    mock_record = MagicMock()
    mock_record.provider_id = 99
    db.get_record.return_value = mock_record

    result = add_prescription(1, "Amoxicillin", "500mg", "daily", 10, 99)

    assert db.get_record.return_value.provider_id == 99
    assert result == 101


# PArt 3.2
    

def test_du_rx_id_returned_correctly():
    """DU pair for rx: def N11 -> use N13, rx.id is returned correctly."""
    mock_record = MagicMock()
    mock_record.provider_id = 99
    db.get_record.return_value = mock_record

    result = add_prescription(1, "Amoxicillin", "500mg", "daily", 10, 99)

    assert result == 101