"""Corporate Income Tax (CIT) Module for Uganda.

Implements corporate tax calculation under the Uganda Income Tax Act (Cap 340):
- Resident corporate tax rate: 30%
- Chargeable income = Gross Revenue - Allowable Deductions (Section 22)
- Assessed tax losses carried forward (Section 38)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Any, List
from .money import Money
from .exceptions import InvalidIncomeError
from .base import Tax, TaxContext, TaxResult


@dataclass(frozen=True)
class CorporateAssessment:
    """Detailed corporate tax return and assessment report."""
    gross_revenue: Money
    allowable_deductions: Money
    disallowed_deductions: Money
    loss_brought_forward: Money
    adjusted_gross_profit: Money
    chargeable_income: Money
    loss_carried_forward: Money
    tax_rate: Decimal
    tax_payable: Money
    effective_rate_on_revenue: Decimal
    audit_notes: List[str] = field(default_factory=list)


class CorporateIncomeTax(Tax):
    """Uganda Corporate Income Tax calculator."""

    STANDARD_RESIDENT_RATE = Decimal("0.30")

    def __init__(self, tax_rate: Decimal = STANDARD_RESIDENT_RATE) -> None:
        super().__init__(
            name="Uganda Corporate Income Tax",
            description="Resident company corporate income tax at 30% on net chargeable income",
        )
        self.tax_rate = tax_rate

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate corporate tax via standard Tax contract.

        Interprets ctx.gross_amount as chargeable income (or computes revenue minus deductions if in metadata).
        """
        if ctx.gross_amount.is_negative():
            raise InvalidIncomeError(f"Chargeable income cannot be negative: {ctx.gross_amount}")

        allowable = ctx.metadata.get("allowable_deductions", Money.zero())
        if allowable.is_negative():
            raise InvalidIncomeError(f"Allowable deductions cannot be negative: {allowable}")

        chargeable = max(Money.zero(), ctx.gross_amount - allowable)
        tax_payable = chargeable * self.tax_rate

        effective_rate = (
            (tax_payable.amount / ctx.gross_amount.amount).quantize(Decimal("0.0001"))
            if ctx.gross_amount > Money.zero()
            else Decimal("0.0000")
        )

        return TaxResult(
            tax_payable=tax_payable,
            taxable_base=chargeable,
            effective_rate=effective_rate,
            marginal_rate=self.tax_rate,
            summary=f"Corporate Income Tax on chargeable income of {chargeable} is {tax_payable}",
            metadata={
                "tax_rate": f"{self.tax_rate * 100:.0f}%",
                "gross_revenue": str(ctx.gross_amount),
                "allowable_deductions": str(allowable),
            },
        )

    def assess(
        self,
        gross_revenue: Money,
        allowable_deductions: Money = Money.zero(),
        disallowed_deductions: Money = Money.zero(),
        loss_brought_forward: Money = Money.zero(),
    ) -> CorporateAssessment:
        """Perform full statutory corporate tax assessment.

        Args:
            gross_revenue: Total gross sales/operating turnover in UGX.
            allowable_deductions: Expenses wholly and exclusively incurred in the production
                                 of income (ITA Section 22).
            disallowed_deductions: Non-deductible items (fines, non-business costs, capital expense).
            loss_brought_forward: Assessed tax losses carried forward from previous tax years (ITA Section 38).

        Returns:
            CorporateAssessment detailing chargeable income, loss carryforwards, and CIT liability.
        """
        if gross_revenue.is_negative():
            raise InvalidIncomeError(f"Gross revenue cannot be negative: {gross_revenue}")
        if allowable_deductions.is_negative():
            raise InvalidIncomeError(f"Allowable deductions cannot be negative: {allowable_deductions}")
        if disallowed_deductions.is_negative():
            raise InvalidIncomeError(f"Disallowed deductions cannot be negative: {disallowed_deductions}")
        if loss_brought_forward.is_negative():
            raise InvalidIncomeError(f"Loss brought forward cannot be negative: {loss_brought_forward}")

        zero = Money.zero()
        notes: List[str] = []

        # Operating profit before loss relief
        operating_surplus = gross_revenue - allowable_deductions

        if operating_surplus > zero:
            # Company generated taxable surplus this year
            notes.append(f"Operating surplus of {operating_surplus} generated before prior loss relief.")
            if loss_brought_forward > zero:
                if operating_surplus >= loss_brought_forward:
                    chargeable_income = operating_surplus - loss_brought_forward
                    loss_carried_forward = zero
                    notes.append(f"Fully utilized prior loss of {loss_brought_forward}. Net chargeable: {chargeable_income}.")
                else:
                    chargeable_income = zero
                    loss_carried_forward = loss_brought_forward - operating_surplus
                    notes.append(f"Partially utilized prior loss. Remaining loss to carry forward: {loss_carried_forward}.")
            else:
                chargeable_income = operating_surplus
                loss_carried_forward = zero
        else:
            # Operating loss incurred this year
            current_loss = allowable_deductions - gross_revenue
            chargeable_income = zero
            loss_carried_forward = loss_brought_forward + current_loss
            notes.append(f"Current year tax loss of {current_loss} added to cumulative loss carryforward.")

        tax_payable = chargeable_income * self.tax_rate

        effective_rate = (
            (tax_payable.amount / gross_revenue.amount).quantize(Decimal("0.0001"))
            if gross_revenue > zero
            else Decimal("0.0000")
        )

        return CorporateAssessment(
            gross_revenue=gross_revenue,
            allowable_deductions=allowable_deductions,
            disallowed_deductions=disallowed_deductions,
            loss_brought_forward=loss_brought_forward,
            adjusted_gross_profit=operating_surplus,
            chargeable_income=chargeable_income,
            loss_carried_forward=loss_carried_forward,
            tax_rate=self.tax_rate,
            tax_payable=tax_payable,
            effective_rate_on_revenue=effective_rate,
            audit_notes=notes,
        )

