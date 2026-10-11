"""Property-based tests with Hypothesis for the Uganda Tax Engine.

Properties verified:
1. Tax must be non-negative: tax(x) >= 0 for all x >= 0.
2. Tax must be monotonic in income: x1 <= x2 ==> tax(x1) <= tax(x2).
3. Tax must never exceed income: tax(x) <= x for all x >= 0.
4. Non-resident tax liability is greater than or equal to resident tax: tax_nr(x) >= tax_r(x).
5. Post-tax take-home income is monotonic: x1 <= x2 ==> (x1 - tax(x1)) <= (x2 - tax(x2)).
"""

from decimal import Decimal
from hypothesis import given, settings, strategies as st
from src.tax_engine.money import Money
from src.tax_engine.base import TaxContext, ResidencyStatus
from src.tax_engine.paye import PAYETax


paye = PAYETax(schedule_year=2026)

# Generate non-negative incomes up to 100 million UGX
income_strategy = st.integers(min_value=0, max_value=100_000_000)


@given(income=income_strategy)
@settings(max_examples=100)
def test_property_tax_is_non_negative_resident(income: int):
    """Property 1: Tax must be non-negative for resident individuals."""
    m_income = Money(income)
    ctx = TaxContext(gross_amount=m_income, residency=ResidencyStatus.RESIDENT)
    result = paye.calculate(ctx)
    assert result.tax_payable >= Money.zero(), f"Tax was negative for income {income}: {result.tax_payable}"


@given(income=income_strategy)
@settings(max_examples=100)
def test_property_tax_is_non_negative_non_resident(income: int):
    """Property 1b: Tax must be non-negative for non-resident individuals."""
    m_income = Money(income)
    ctx = TaxContext(gross_amount=m_income, residency=ResidencyStatus.NON_RESIDENT)
    result = paye.calculate(ctx)
    assert result.tax_payable >= Money.zero(), f"Tax was negative for non-resident income {income}: {result.tax_payable}"


@given(
    inc1=st.integers(min_value=0, max_value=50_000_000),
    inc2=st.integers(min_value=0, max_value=50_000_000),
)
@settings(max_examples=100)
def test_property_tax_is_monotonic_in_income_resident(inc1: int, inc2: int):
    """Property 2: Monotonicity - higher income must never result in lower tax."""
    lower_val, higher_val = sorted([inc1, inc2])
    ctx_low = TaxContext(gross_amount=Money(lower_val), residency=ResidencyStatus.RESIDENT)
    ctx_high = TaxContext(gross_amount=Money(higher_val), residency=ResidencyStatus.RESIDENT)

    tax_low = paye.calculate(ctx_low).tax_payable
    tax_high = paye.calculate(ctx_high).tax_payable

    assert tax_low <= tax_high, (
        f"Monotonicity violated for resident: tax({lower_val}) = {tax_low} > tax({higher_val}) = {tax_high}"
    )


@given(income=income_strategy)
@settings(max_examples=100)
def test_property_tax_never_exceeds_income_resident(income: int):
    """Property 3: Tax must never exceed gross income."""
    m_income = Money(income)
    ctx = TaxContext(gross_amount=m_income, residency=ResidencyStatus.RESIDENT)
    result = paye.calculate(ctx)
    assert result.tax_payable <= m_income, (
        f"Tax exceeded gross income: income={m_income}, tax={result.tax_payable}"
    )


@given(income=income_strategy)
@settings(max_examples=100)
def test_property_tax_never_exceeds_income_non_resident(income: int):
    """Property 3b: Tax must never exceed gross income for non-residents."""
    m_income = Money(income)
    ctx = TaxContext(gross_amount=m_income, residency=ResidencyStatus.NON_RESIDENT)
    result = paye.calculate(ctx)
    assert result.tax_payable <= m_income, (
        f"Non-resident tax exceeded income: income={m_income}, tax={result.tax_payable}"
    )


@given(income=income_strategy)
@settings(max_examples=100)
def test_property_non_resident_tax_ge_resident_tax(income: int):
    """Property 4: Non-resident tax liability is >= resident tax liability across all incomes."""
    m_income = Money(income)
    ctx_res = TaxContext(gross_amount=m_income, residency=ResidencyStatus.RESIDENT)
    ctx_non_res = TaxContext(gross_amount=m_income, residency=ResidencyStatus.NON_RESIDENT)

    tax_res = paye.calculate(ctx_res).tax_payable
    tax_non_res = paye.calculate(ctx_non_res).tax_payable

    assert tax_non_res >= tax_res, (
        f"Non-resident tax ({tax_non_res}) was lower than resident tax ({tax_res}) for income {income}"
    )


@given(
    inc1=st.integers(min_value=0, max_value=50_000_000),
    inc2=st.integers(min_value=0, max_value=50_000_000),
)
@settings(max_examples=100)
def test_property_net_take_home_is_monotonic(inc1: int, inc2: int):
    """Property 5: Take-home pay (income - tax) must be non-decreasing with income (no 100%+ marginal cliff)."""
    low_val, high_val = sorted([inc1, inc2])
    m_low, m_high = Money(low_val), Money(high_val)

    tax_low = paye.calculate(TaxContext(gross_amount=m_low, residency=ResidencyStatus.RESIDENT)).tax_payable
    tax_high = paye.calculate(TaxContext(gross_amount=m_high, residency=ResidencyStatus.RESIDENT)).tax_payable

    net_low = m_low - tax_low
    net_high = m_high - tax_high

    assert net_low <= net_high, (
        f"Take-home anomaly: earn {low_val} take home {net_low}, earn {high_val} take home {net_high}"
    )

