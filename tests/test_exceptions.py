"""Unit tests for the custom exception hierarchy and input validation."""

import pytest
from datetime import date
from src.tax_engine.money import Money
from src.tax_engine.base import TaxContext, ResidencyStatus
from src.tax_engine.paye import PAYETax
from src.tax_engine.exceptions import (
    TaxError,
    InvalidIncomeError,
    NoScheduleForDateError,
    CurrencyMismatchError,
    NegativeValueError,
    InvalidSupplyTypeError,
    TaxValidationError,
)


def test_exception_inheritance():
    assert issubclass(InvalidIncomeError, TaxError)
    assert issubclass(NoScheduleForDateError, TaxError)
    assert issubclass(CurrencyMismatchError, TaxError)
    assert issubclass(NegativeValueError, TaxError)
    assert issubclass(InvalidSupplyTypeError, TaxError)
    assert issubclass(TaxValidationError, TaxError)


def test_no_schedule_for_unsupported_date():
    engine = PAYETax()
    # Past year out of range
    ctx_past = TaxContext(
        gross_amount=Money("1000000"),
        effective_date=date(1990, 1, 1),
    )
    with pytest.raises(NoScheduleForDateError, match="No statutory PAYE schedule defined for year 1990"):
        engine.calculate(ctx_past)

    # Far future year out of range
    ctx_future = TaxContext(
        gross_amount=Money("1000000"),
        effective_date=date(2055, 1, 1),
    )
    with pytest.raises(NoScheduleForDateError, match="No statutory PAYE schedule defined for year 2055"):
        engine.calculate(ctx_future)


def test_negative_income_raises_immediately():
    with pytest.raises(InvalidIncomeError):
        _ = TaxContext(gross_amount=Money("-50000"))

    with pytest.raises(InvalidIncomeError):
        _ = TaxContext(gross_amount=Money("50000"), allowances=Money("-1000"))

