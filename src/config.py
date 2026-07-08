"""MediTrack configuration constants."""

CLINIC_OPEN_HOUR = 8    # 8:00 AM
CLINIC_CLOSE_HOUR = 17  # 5:00 PM

VALID_APPOINTMENT_TYPES = [
    'new_patient',
    'follow_up',
    'urgent_care',
    'procedure',
    'telehealth',
]

VALID_DURATIONS = [15, 30, 45, 60]  # minutes

VALID_FREQUENCIES = [
    'once_daily',
    'twice_daily',
    'three_times_daily',
    'as_needed',
    'weekly',
]

VALID_PAYMENT_METHODS = ['cash', 'credit_card', 'debit_card', 'check', 'insurance']

APPOINTMENT_STATES = ['Scheduled', 'CheckedIn', 'InProgress', 'Completed', 'Cancelled', 'NoShow']

INVOICE_STATES = ['Draft', 'Submitted', 'PartiallyPaid', 'Paid', 'Voided']

LATE_CANCEL_HOURS = 24  # hours before appointment

MAX_NAME_LENGTH = 50
MIN_NAME_LENGTH = 1
PHONE_LENGTH = 10
MAX_EMAIL_LENGTH = 100
MIN_INSURANCE_ID_LENGTH = 6
MAX_INSURANCE_ID_LENGTH = 20

MIN_DAYS_SUPPLY = 1
MAX_DAYS_SUPPLY = 365

MIN_CHIEF_COMPLAINT = 1
MAX_CHIEF_COMPLAINT = 500

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100

import re
ICD_PATTERN = re.compile(r'^[A-Z][0-9]{2}(\.[A-Z0-9]{1,4})?$')
