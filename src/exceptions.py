"""MediTrack custom exceptions."""

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass

class AuthError(Exception):
    """Raised for authentication or authorization failures."""
    pass

class SessionExpiredError(Exception):
    """Raised when a session token has expired."""
    pass

class SchedulingConflict(Exception):
    """Raised when an appointment would cause a double-booking."""
    pass

class InvalidStateError(Exception):
    """Raised when an operation is not valid for the current object state."""
    pass

class DuplicateInvoiceError(Exception):
    """Raised when trying to create a second invoice for an appointment."""
    pass

class InsuranceNotFoundError(Exception):
    """Raised when an insurance ID is not found in the system."""
    pass
