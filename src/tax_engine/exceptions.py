"""Custom exception hierarchy for the Uganda Tax Engine.

All domain exceptions inherit from TaxError, ensuring clear error classification
and strict validation without silent failures.
"""


class TaxError(Exception):
    """Base exception for all tax engine domain errors."""
    pass


class InvalidIncomeError(TaxError):
    """Raised when an income value is invalid (e.g., negative or non-numeric)."""
    pass


class NoScheduleForDateError(TaxError):
    """Raised when no statutory tax schedule exists for the specified tax date or year."""
    pass


class CurrencyMismatchError(TaxError):
    """Raised when operations are attempted between incompatible currencies."""
    pass


class NegativeValueError(TaxError):
    """Raised when a non-negative monetary quantity is negative."""
    pass


class InvalidSupplyTypeError(TaxError):
    """Raised when an unrecognized VAT supply type is provided."""
    pass


class TaxValidationError(TaxError):
    """Raised when input parameters fail domain validation constraints."""
    pass

