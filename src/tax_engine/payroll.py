"""Payroll pipeline module for Ugandan employers.

Models comprehensive employment deductions:
- Gross Pay (Basic + Allowances)
- National Social Security Fund (NSSF: 5% Employee, 10% Employer)
- Local Service Tax (LST: pre-tax deduction per Local Governments Act)
- PAYE (Resident / Non-Resident progressive tax)
- Net Pay and Employer Total Cost to Company (CTC)

Deduction Order & Regulatory Justification:
1. Gross Employment Income: Aggregate of basic salary and all taxable allowances
   (Section 19, Uganda Income Tax Act).
2. Local Service Tax (LST): Deducted pre-PAYE. Under the Local Governments (Amendment)
   Act and URA Practice Notes, statutory local government taxes paid by employees are
   an allowable deduction from gross employment income prior to calculating PAYE taxable base.
3. Taxable Pay Base: Gross pay less allowable pre-tax deductions (LST).
4. PAYE Tax: Progressive bands applied on the adjusted taxable base.
5. Employee NSSF (5%): Statutory retirement contribution deducted from gross earnings.
   Under current URA practice, mandatory statutory NSSF is not exempt from the PAYE base
   for private employees, hence calculated as 5% of gross cash remuneration.
6. Net Pay: Gross Remuneration - Employee NSSF - LST - PAYE Tax.
7. Employer NSSF (10%): Mandatory employer contribution added to employer liability
   (Total Cost to Company = Gross + Employer NSSF).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Any, List, Optional
from .money import Money
from .exceptions import InvalidIncomeError
from .base import ResidencyStatus, TaxContext, TaxResult
from .paye import PAYETax


@dataclass(frozen=True)
class PayrollSlip:
    """Detailed payroll summary for an employee."""
    basic_salary: Money
    cash_allowances: Money
    gross_pay: Money
    employee_nssf: Money
    employer_nssf: Money
    total_nssf: Money
    lst: Money
    taxable_paye_base: Money
    paye_result: TaxResult
    total_deductions: Money
    net_pay: Money
    total_employer_cost: Money
    deduction_trail: List[Dict[str, Any]] = field(default_factory=list)


class PayrollPipeline:
    """Configurable payroll calculation pipeline."""

    NSSF_EMPLOYEE_RATE = Decimal("0.05")
    NSSF_EMPLOYER_RATE = Decimal("0.10")

    def __init__(self, paye_tax: Optional[PAYETax] = None) -> None:
        self.paye_tax = paye_tax or PAYETax()

    def process(
        self,
        basic_salary: Money,
        cash_allowances: Money = Money.zero(),
        residency: ResidencyStatus = ResidencyStatus.RESIDENT,
        lst_deduction: Money = Money.zero(),
        lst_is_pre_tax: bool = True,
    ) -> PayrollSlip:
        """Run payroll calculations for an individual employee.

        Args:
            basic_salary: Base monthly salary in UGX.
            cash_allowances: Cash allowances (housing, transport, etc.) in UGX.
            residency: Residency status for PAYE calculation.
            lst_deduction: Local Service Tax monthly deduction in UGX.
            lst_is_pre_tax: If True, LST is deducted from gross income before computing PAYE.

        Returns:
            PayrollSlip containing net pay, all deductions, and audit trail.
        """
        if basic_salary.is_negative():
            raise InvalidIncomeError(f"Basic salary cannot be negative: {basic_salary}")
        if cash_allowances.is_negative():
            raise InvalidIncomeError(f"Cash allowances cannot be negative: {cash_allowances}")
        if lst_deduction.is_negative():
            raise InvalidIncomeError(f"LST deduction cannot be negative: {lst_deduction}")

        # 1. Gross Earnings
        gross_pay = basic_salary + cash_allowances

        # 2. NSSF Contributions (5% employee, 10% employer)
        employee_nssf = gross_pay * self.NSSF_EMPLOYEE_RATE
        employer_nssf = gross_pay * self.NSSF_EMPLOYER_RATE
        total_nssf = employee_nssf + employer_nssf

        # 3. Pre-tax LST deduction determination
        if lst_is_pre_tax:
            taxable_paye_base = max(Money.zero(), gross_pay - lst_deduction)
        else:
            taxable_paye_base = gross_pay

        # 4. PAYE calculation
        ctx = TaxContext(
            gross_amount=taxable_paye_base,
            allowances=Money.zero(),
            residency=residency,
        )
        paye_result = self.paye_tax.calculate(ctx)
        paye_amount = paye_result.tax_payable

        # 5. Total employee deductions & Net Pay
        total_deductions = employee_nssf + lst_deduction + paye_amount
        net_pay = gross_pay - total_deductions

        # 6. Total Cost to Company (CTC)
        total_employer_cost = gross_pay + employer_nssf

        # Audit trail
        trail: List[Dict[str, Any]] = [
            {
                "step": 1,
                "description": "Gross Earnings (Basic + Allowances)",
                "amount": gross_pay,
                "notes": "ITA Section 19 employment income aggregation",
            },
            {
                "step": 2,
                "description": "Local Service Tax (LST)",
                "amount": lst_deduction,
                "notes": "Allowable pre-PAYE deduction per Local Governments Act" if lst_is_pre_tax else "Post-tax deduction",
            },
            {
                "step": 3,
                "description": "Taxable PAYE Base",
                "amount": taxable_paye_base,
                "notes": "Base subjected to statutory PAYE progressive bands",
            },
            {
                "step": 4,
                "description": "PAYE Tax Liability",
                "amount": paye_amount,
                "notes": f"Progressive bands result ({residency.value})",
            },
            {
                "step": 5,
                "description": "Employee NSSF (5%)",
                "amount": employee_nssf,
                "notes": "Statutory social security deduction (NSSF Act)",
            },
            {
                "step": 6,
                "description": "Net Pay to Employee",
                "amount": net_pay,
                "notes": "Gross Pay minus Employee NSSF, LST, and PAYE",
            },
            {
                "step": 7,
                "description": "Employer NSSF (10%)",
                "amount": employer_nssf,
                "notes": "Employer statutory matching liability",
            },
            {
                "step": 8,
                "description": "Total Cost to Company (CTC)",
                "amount": total_employer_cost,
                "notes": "Gross Remuneration + Employer NSSF",
            },
        ]

        return PayrollSlip(
            basic_salary=basic_salary,
            cash_allowances=cash_allowances,
            gross_pay=gross_pay,
            employee_nssf=employee_nssf,
            employer_nssf=employer_nssf,
            total_nssf=total_nssf,
            lst=lst_deduction,
            taxable_paye_base=taxable_paye_base,
            paye_result=paye_result,
            total_deductions=total_deductions,
            net_pay=net_pay,
            total_employer_cost=total_employer_cost,
            deduction_trail=trail,
        )

