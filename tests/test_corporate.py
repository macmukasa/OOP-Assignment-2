"""Unit tests for Corporate Income Tax (CIT) Module."""

import pytest
from decimal import Decimal
from src.tax_engine.money import Money
from src.tax_engine.corporate import CorporateIncomeTax
from src.tax_engine.base import TaxContext
from src.tax_engine.exceptions import InvalidIncomeError


@pytest.fixture
def cit_engine() -> CorporateIncomeTax:
    return CorporateIncomeTax()


def test_cit_standard_profitable_company(cit_engine: CorporateIncomeTax):
    # Gross Revenue: 100,000,000 UGX
    # Allowable Deductions: 60,000,000 UGX
    # Chargeable Income: 40,000,000 UGX
    # Tax @ 30%: 12,000,000 UGX
    assessment = cit_engine.assess(
        gross_revenue=Money("100000000"),
        allowable_deductions=Money("60000000"),
    )

    assert assessment.adjusted_gross_profit == Money("40000000.00")
    assert assessment.chargeable_income == Money("40000000.00")
    assert assessment.tax_payable == Money("12000000.00")
    assert assessment.loss_carried_forward == Money.zero()
    assert assessment.effective_rate_on_revenue == Decimal("0.1200")


def test_cit_tax_base_contract(cit_engine: CorporateIncomeTax):
    # Testing calculate method conforming to Tax abstract contract
    ctx = TaxContext(
        gross_amount=Money("50000000"),
        metadata={"allowable_deductions": Money("20000000")},
    )
    result = cit_engine.calculate(ctx)

    # Chargeable = 30,000,000, Tax @ 30% = 9,000,000
    assert result.taxable_base == Money("30000000.00")
    assert result.tax_payable == Money("9000000.00")
    assert result.marginal_rate == Decimal("0.30")


def test_cit_loss_scenario(cit_engine: CorporateIncomeTax):
    # Revenue: 50,000,000 UGX
    # Allowable expenses: 70,000,000 UGX
    # Current loss = 20,000,000 UGX
    assessment = cit_engine.assess(
        gross_revenue=Money("50000000"),
        allowable_deductions=Money("70000000"),
    )

    assert assessment.chargeable_income == Money.zero()
    assert assessment.tax_payable == Money.zero()
    assert assessment.loss_carried_forward == Money("20000000.00")


def test_cit_prior_loss_utilization(cit_engine: CorporateIncomeTax):
    # Current operating surplus: 40,000,000 UGX
    # Prior loss brought forward: 15,000,000 UGX
    # Net chargeable income: 25,000,000 UGX
    # Tax @ 30%: 7,500,000 UGX
    assessment = cit_engine.assess(
        gross_revenue=Money("100000000"),
        allowable_deductions=Money("60000000"),
        loss_brought_forward=Money("15000000"),
    )

    assert assessment.chargeable_income == Money("25000000.00")
    assert assessment.loss_carried_forward == Money.zero()
    assert assessment.tax_payable == Money("7500000.00")


def test_cit_negative_inputs_raise(cit_engine: CorporateIncomeTax):
    with pytest.raises(InvalidIncomeError):
        cit_engine.assess(gross_revenue=Money("-100000"))

    with pytest.raises(InvalidIncomeError):
        cit_engine.assess(gross_revenue=Money("100000"), allowable_deductions=Money("-500"))

