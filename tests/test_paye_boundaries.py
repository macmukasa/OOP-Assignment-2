"""Boundary tests for PAYE tax schedules at every statutory band edge.

Boundary edges:
- 335,000 UGX
- 335,001 UGX
- 410,000 UGX
- 485,000 UGX
- 10,000,000 UGX
- 10,000,001 UGX
"""

import pytest
from decimal import Decimal
from src.tax_engine.money import Money
from src.tax_engine.base import TaxContext, ResidencyStatus
from src.tax_engine.paye import PAYETax


@pytest.fixture
def paye_engine() -> PAYETax:
    return PAYETax(schedule_year=2026)


# Resident boundary tests
@pytest.mark.parametrize(
    "gross_income, expected_tax_str",
    [
        ("0", "0.00"),
        ("100000", "0.00"),
        ("335000", "0.00"),            # Lower threshold edge
        ("335001", "0.20"),            # Edge + 1 UGX (20% marginal tier starts)
        ("410000", "15000.00"),        # Second threshold edge
        ("410001", "15000.25"),        # Edge + 1 UGX (25% marginal tier starts)
        ("485000", "33750.00"),        # Third threshold edge
        ("485001", "33750.30"),        # Edge + 1 UGX (30% marginal tier starts)
        ("10000000", "2888250.00"),    # Surcharge threshold edge
        ("10000001", "2888250.40"),    # Edge + 1 UGX (40% combined surcharge starts)
        ("15000000", "4888250.00"),    # High-income bracket
    ],
)
def test_resident_paye_boundaries(paye_engine: PAYETax, gross_income: str, expected_tax_str: str):
    ctx = TaxContext(
        gross_amount=Money(gross_income),
        residency=ResidencyStatus.RESIDENT,
    )
    result = paye_engine.calculate(ctx)
    expected_tax = Money(expected_tax_str)
    assert result.tax_payable == expected_tax, (
        f"Resident PAYE mismatch for income {gross_income}: expected {expected_tax}, got {result.tax_payable}"
    )


# Non-resident boundary tests
@pytest.mark.parametrize(
    "gross_income, expected_tax_str",
    [
        ("0", "0.00"),
        ("335000", "33500.00"),        # 10% flat on first 335,000
        ("335001", "33500.20"),        # First edge + 1 UGX
        ("410000", "48500.00"),        # Second threshold edge
        ("485000", "67250.00"),        # Third threshold edge
        ("10000000", "2921750.00"),    # Surcharge threshold edge
        ("10000001", "2921750.40"),    # Surcharge threshold edge + 1 UGX
    ],
)
def test_non_resident_paye_boundaries(paye_engine: PAYETax, gross_income: str, expected_tax_str: str):
    ctx = TaxContext(
        gross_amount=Money(gross_income),
        residency=ResidencyStatus.NON_RESIDENT,
    )
    result = paye_engine.calculate(ctx)
    expected_tax = Money(expected_tax_str)
    assert result.tax_payable == expected_tax, (
        f"Non-Resident PAYE mismatch for income {gross_income}: expected {expected_tax}, got {result.tax_payable}"
    )


def test_paye_with_allowances(paye_engine: PAYETax):
    # Gross salary 300,000 + Allowance 100,000 = Total 400,000
    # Resident PAYE on 400,000: 20% of (400,000 - 335,000) = 20% of 65,000 = 13,000
    ctx = TaxContext(
        gross_amount=Money("300000"),
        allowances=Money("100000"),
        residency=ResidencyStatus.RESIDENT,
    )
    result = paye_engine.calculate(ctx)
    assert result.tax_payable == Money("13000.00")
    assert result.taxable_base == Money("400000.00")

