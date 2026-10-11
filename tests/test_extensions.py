"""Unit tests for Extension Task A: Withholding Tax and Rental Income Tax."""

import pytest
from decimal import Decimal
from src.tax_engine.money import Money
from src.tax_engine.extensions import (
    WithholdingTax,
    WHTCategory,
    RentalIncomeTax,
)
from src.tax_engine.base import TaxContext
from src.tax_engine.exceptions import InvalidIncomeError


# --- Withholding Tax Tests ---

@pytest.fixture
def wht_engine() -> WithholdingTax:
    return WithholdingTax()


def test_wht_goods_above_threshold(wht_engine: WithholdingTax):
    # Payment of 2,000,000 UGX for goods (> 1,000,000 threshold)
    # WHT @ 6% = 120,000 UGX, Net payable = 1,880,000 UGX
    res = wht_engine.withhold(Money("2000000"), category=WHTCategory.GOODS_AND_SERVICES)

    assert res.wht_withheld == Money("1200000.00") * Decimal("0.10")  # 120,000
    assert res.wht_withheld == Money("120000.00")
    assert res.net_payable_to_vendor == Money("1880000.00")
    assert res.rate_percent == Decimal("6.0")
    assert not res.exemption_applied


def test_wht_goods_below_or_equal_threshold(wht_engine: WithholdingTax):
    # Exactly 1,000,000 UGX: Section 119 threshold is "exceeds 1,000,000"
    res_edge = wht_engine.withhold(Money("1000000"), category=WHTCategory.GOODS_AND_SERVICES)
    assert res_edge.wht_withheld == Money.zero()
    assert res_edge.net_payable_to_vendor == Money("1000000.00")

    # Below 1,000,000 UGX
    res_below = wht_engine.withhold(Money("500000"), category=WHTCategory.GOODS_AND_SERVICES)
    assert res_below.wht_withheld == Money.zero()
    assert res_below.net_payable_to_vendor == Money("500000.00")


def test_wht_professional_fees(wht_engine: WithholdingTax):
    # Professional fees of 500,000 UGX: Flat 15% under Section 119A
    # WHT = 75,000 UGX, Net = 425,000 UGX
    res = wht_engine.withhold(Money("500000"), category=WHTCategory.PROFESSIONAL_FEES)

    assert res.wht_withheld == Money("75000.00")
    assert res.net_payable_to_vendor == Money("425000.00")
    assert res.rate_percent == Decimal("15.0")


def test_wht_with_exemption_certificate(wht_engine: WithholdingTax):
    # Valid URA exemption certificate
    res = wht_engine.withhold(Money("50000000"), category=WHTCategory.GOODS_AND_SERVICES, has_exemption=True)
    assert res.wht_withheld == Money.zero()
    assert res.net_payable_to_vendor == Money("50000000.00")
    assert res.exemption_applied


# --- Rental Income Tax Tests ---

@pytest.fixture
def rental_monthly_engine() -> RentalIncomeTax:
    return RentalIncomeTax(is_annual=False)


@pytest.fixture
def rental_annual_engine() -> RentalIncomeTax:
    return RentalIncomeTax(is_annual=True)


def test_rental_tax_monthly_above_threshold(rental_monthly_engine: RentalIncomeTax):
    # Monthly gross rent = 1,000,000 UGX
    # Threshold = 235,000 UGX
    # Taxable rent = 765,000 UGX
    # Tax @ 12% = 91,800 UGX
    # Net rent = 908,200 UGX
    res = rental_monthly_engine.assess_individual(Money("1000000"))

    assert res.taxable_rent == Money("765000.00")
    assert res.tax_payable == Money("91800.00")
    assert res.net_rental_income == Money("908200.00")
    assert res.tax_rate == Decimal("0.12")


def test_rental_tax_monthly_below_threshold(rental_monthly_engine: RentalIncomeTax):
    # Rent <= 235,000 -> Nil tax
    res = rental_monthly_engine.assess_individual(Money("200000"))

    assert res.taxable_rent == Money.zero()
    assert res.tax_payable == Money.zero()
    assert res.net_rental_income == Money("200000.00")


def test_rental_tax_annual_assessment(rental_annual_engine: RentalIncomeTax):
    # Annual gross rent = 12,000,000 UGX
    # Annual threshold = 2,820,000 UGX
    # Taxable rent = 9,180,000 UGX
    # Tax @ 12% = 1,101,600 UGX
    res = rental_annual_engine.assess_individual(Money("12000000"))

    assert res.taxable_rent == Money("9180000.00")
    assert res.tax_payable == Money("1101600.00")
    assert res.net_rental_income == Money("10898400.00")


def test_rental_tax_negative_input_raises(rental_monthly_engine: RentalIncomeTax):
    with pytest.raises(InvalidIncomeError):
        rental_monthly_engine.assess_individual(Money("-50000"))

