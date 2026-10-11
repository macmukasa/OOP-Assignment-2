"""Unit tests for Money Value Object."""

import pytest
from decimal import Decimal
from src.tax_engine.money import Money
from src.tax_engine.exceptions import CurrencyMismatchError, InvalidIncomeError


def test_money_creation_valid():
    m1 = Money(Decimal("335000.00"))
    m2 = Money("335000")
    m3 = Money(335000)
    assert m1.amount == Decimal("335000.00")
    assert m2.amount == Decimal("335000.00")
    assert m3.amount == Decimal("335000.00")
    assert m1.currency == "UGX"


def test_money_rejects_float():
    with pytest.raises(TypeError, match="Floating-point value .* is strictly forbidden"):
        Money(335000.50)

    with pytest.raises(TypeError, match="Multiplication by float .* is forbidden"):
        Money("1000") * 0.18

    with pytest.raises(TypeError, match="Division by float .* is forbidden"):
        Money("1000") / 2.0


def test_money_rejects_invalid_string():
    with pytest.raises(InvalidIncomeError):
        Money("not-a-number")


def test_money_arithmetic_addition_and_subtraction():
    a = Money("500000")
    b = Money("250000")
    assert a + b == Money("750000")
    assert a - b == Money("250000")


def test_money_sum_builtin():
    items = [Money("10000"), Money("20000"), Money("30000")]
    assert sum(items, Money.zero()) == Money("60000")
    assert sum(items) == Money("60000")


def test_money_multiplication_and_division():
    m = Money("100000")
    # Scalar multiplication with Decimal and int
    assert m * 2 == Money("200000")
    assert 2 * m == Money("200000")
    assert m * Decimal("0.18") == Money("18000.00")
    assert Decimal("0.18") * m == Money("18000.00")

    # Division by scalar
    assert m / 2 == Money("50000.00")
    assert m / Decimal("4") == Money("25000.00")

    # Division of Money by Money yields Decimal ratio
    ratio = Money("18000") / Money("100000")
    assert ratio == Decimal("0.18")


def test_money_zero_division():
    with pytest.raises(ZeroDivisionError):
        _ = Money("100") / 0
    with pytest.raises(ZeroDivisionError):
        _ = Money("100") / Money.zero()


def test_money_comparisons():
    m1 = Money("100")
    m2 = Money("200")
    m3 = Money("100")

    assert m1 < m2
    assert m1 <= m2
    assert m1 <= m3
    assert m2 > m1
    assert m2 >= m1
    assert m1 == m3
    assert m1 != m2


def test_money_currency_mismatch():
    ugx = Money("1000", currency="UGX")
    usd = Money("1000", currency="USD")

    with pytest.raises(CurrencyMismatchError):
        _ = ugx + usd

    with pytest.raises(CurrencyMismatchError):
        _ = ugx - usd

    with pytest.raises(CurrencyMismatchError):
        _ = ugx < usd


def test_money_rounding_rules():
    # Explicit ROUND_HALF_UP rounding to shilling
    m = Money("1234.50")
    assert m.round_to_shilling() == Money("1235")

    m2 = Money("1234.49")
    assert m2.round_to_shilling() == Money("1234")


def test_money_immutability():
    m = Money("50000")
    with pytest.raises(AttributeError):
        m._amount = Decimal("60000")  # Slots protection


def test_money_formatting():
    m = Money("10000000")
    assert repr(m) == "Money('10000000.00', currency='UGX')"
    assert str(m) == "UGX 10,000,000.00"
    assert m.format_ugx(with_cents=False) == "UGX 10,000,000"

