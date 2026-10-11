"""Unit tests for PayrollPipeline."""

import pytest
from decimal import Decimal
from src.tax_engine.money import Money
from src.tax_engine.base import ResidencyStatus
from src.tax_engine.payroll import PayrollPipeline
from src.tax_engine.exceptions import InvalidIncomeError


@pytest.fixture
def pipeline() -> PayrollPipeline:
    return PayrollPipeline()


def test_payroll_basic_employee(pipeline: PayrollPipeline):
    # Basic salary: UGX 1,000,000, no allowances, no LST
    slip = pipeline.process(basic_salary=Money("1000000"))

    assert slip.gross_pay == Money("1000000.00")
    # Employee NSSF: 5% of 1,000,000 = 50,000
    assert slip.employee_nssf == Money("50000.00")
    # Employer NSSF: 10% of 1,000,000 = 100,000
    assert slip.employer_nssf == Money("100000.00")
    assert slip.total_nssf == Money("150000.00")

    # PAYE on 1,000,000 resident:
    # 335k-410k: 15,000
    # 410k-485k: 18,750
    # 485k-1,000,000: 30% of 515,000 = 154,500
    # Total PAYE = 33,750 + 154,500 = 188,250
    assert slip.paye_result.tax_payable == Money("188250.00")

    # Net pay = 1,000,000 - 50,000 - 188,250 = 761,750
    assert slip.net_pay == Money("761750.00")

    # Employer CTC = 1,000,000 + 100,000 = 1,100,000
    assert slip.total_employer_cost == Money("1100000.00")


def test_payroll_with_allowances_and_lst(pipeline: PayrollPipeline):
    # Basic 2,000,000, allowance 500,000, LST 20,000 pre-tax
    slip = pipeline.process(
        basic_salary=Money("2000000"),
        cash_allowances=Money("500000"),
        lst_deduction=Money("20000"),
        lst_is_pre_tax=True,
    )

    assert slip.gross_pay == Money("2500000.00")
    assert slip.employee_nssf == Money("125000.00")  # 5% of 2.5M
    assert slip.employer_nssf == Money("250000.00")  # 10% of 2.5M

    # Pre-tax LST deduction: Taxable PAYE base = 2,500,000 - 20,000 = 2,480,000
    assert slip.taxable_paye_base == Money("2480000.00")

    # Net pay reconciliation: Gross - Employee NSSF - LST - PAYE
    expected_net = slip.gross_pay - slip.employee_nssf - slip.lst - slip.paye_result.tax_payable
    assert slip.net_pay == expected_net


def test_payroll_negative_inputs_raise(pipeline: PayrollPipeline):
    with pytest.raises(InvalidIncomeError):
        pipeline.process(basic_salary=Money("-1000"))

    with pytest.raises(InvalidIncomeError):
        pipeline.process(basic_salary=Money("1000"), cash_allowances=Money("-50"))

    with pytest.raises(InvalidIncomeError):
        pipeline.process(basic_salary=Money("1000"), lst_deduction=Money("-10"))

