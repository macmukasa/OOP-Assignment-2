"""Pay As You Earn (PAYE) Tax Module for Uganda.

Implements progressive tax calculations under the Uganda Revenue Authority (URA)
Income Tax Act (Cap 340), First Schedule, Part I (Resident Individuals) and
Part II (Non-Resident Individuals), including the 10% surcharge on income exceeding
UGX 10,000,000.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple
from .money import Money
from .exceptions import InvalidIncomeError, NoScheduleForDateError, TaxValidationError
from .base import Tax, TaxContext, TaxResult, TaxBandAudit, ResidencyStatus


# Minimum and maximum years for which the current statutory PAYE schedule is valid.
# The 10% surcharge on income > 10M was introduced in FY 2012/2013 and remains active.
SUPPORTED_SCHEDULE_YEARS = (2012, 2030)


@dataclass(frozen=True)
class StatutoryBand:
    """Definition of a statutory progressive tax band."""
    name: str
    lower_threshold: Money
    upper_threshold: Optional[Money]  # None indicates no upper bound (open-ended)
    rate: Decimal                     # e.g., Decimal("0.20") for 20%
    is_surcharge: bool = False        # Whether this band is an additional surcharge tier


class PAYETax(Tax):
    """Uganda PAYE Tax Calculator implementing the statutory tax bands.

    Cites:
        - Uganda Income Tax Act (Cap 340), First Schedule.
        - URA Tax Guide & Income Tax (Amendment) Acts.
    """

    # Statutory Resident Monthly Thresholds (UGX)
    RESIDENT_T1 = Money(Decimal("335000"), round_cents=False)
    RESIDENT_T2 = Money(Decimal("410000"), round_cents=False)
    RESIDENT_T3 = Money(Decimal("485000"), round_cents=False)
    SURCHARGE_THRESHOLD = Money(Decimal("10000000"), round_cents=False)

    def __init__(self, schedule_year: int = 2026) -> None:
        super().__init__(
            name="Uganda PAYE Tax",
            description="Progressive monthly employment income tax with resident and non-resident schedules",
        )
        self.schedule_year = schedule_year

    def _validate_date(self, effective_date: Optional[date]) -> None:
        """Verify statutory schedule existence for effective date."""
        year = effective_date.year if effective_date else self.schedule_year
        if not (SUPPORTED_SCHEDULE_YEARS[0] <= year <= SUPPORTED_SCHEDULE_YEARS[1]):
            raise NoScheduleForDateError(
                f"No statutory PAYE schedule defined for year {year}. "
                f"Supported range: {SUPPORTED_SCHEDULE_YEARS[0]}-{SUPPORTED_SCHEDULE_YEARS[1]}."
            )

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate PAYE tax based on gross amount, allowances, and residency.

        Taxable employment income = gross_amount + allowances.
        """
        self._validate_date(ctx.effective_date)

        if ctx.gross_amount.is_negative():
            raise InvalidIncomeError(f"Gross income cannot be negative: {ctx.gross_amount}")
        if ctx.allowances.is_negative():
            raise InvalidIncomeError(f"Allowances cannot be negative: {ctx.allowances}")

        taxable_income = ctx.gross_amount + ctx.allowances

        if ctx.residency == ResidencyStatus.RESIDENT:
            return self._calculate_resident(taxable_income)
        elif ctx.residency == ResidencyStatus.NON_RESIDENT:
            return self._calculate_non_resident(taxable_income)
        else:
            raise TaxValidationError(f"Unsupported residency status: {ctx.residency}")

    def _calculate_resident(self, income: Money) -> TaxResult:
        """Calculate resident PAYE according to statutory progressive bands."""
        bands_audit: List[TaxBandAudit] = []
        zero = Money.zero()
        t1, t2, t3, t_sur = self.RESIDENT_T1, self.RESIDENT_T2, self.RESIDENT_T3, self.SURCHARGE_THRESHOLD

        total_tax = zero

        # Band 1: Up to 335,000 (0%)
        b1_slice = min(income, t1)
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 1 (Up to UGX 335,000)",
                lower_limit=zero,
                upper_limit=t1,
                taxable_slice=b1_slice,
                rate_percent=Decimal("0.0"),
                tax_amount=zero,
            )
        )

        # Band 2: 335,000 to 410,000 (20%)
        if income > t1:
            b2_slice = min(income, t2) - t1
            b2_tax = b2_slice * Decimal("0.20")
            total_tax += b2_tax
        else:
            b2_slice = zero
            b2_tax = zero
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 2 (UGX 335,000 to 410,000)",
                lower_limit=t1,
                upper_limit=t2,
                taxable_slice=b2_slice,
                rate_percent=Decimal("20.0"),
                tax_amount=b2_tax,
            )
        )

        # Band 3: 410,000 to 485,000 (25%)
        if income > t2:
            b3_slice = min(income, t3) - t2
            b3_tax = b3_slice * Decimal("0.25")
            total_tax += b3_tax
        else:
            b3_slice = zero
            b3_tax = zero
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 3 (UGX 410,000 to 485,000)",
                lower_limit=t2,
                upper_limit=t3,
                taxable_slice=b3_slice,
                rate_percent=Decimal("25.0"),
                tax_amount=b3_tax,
            )
        )

        # Band 4: 485,000 to 10,000,000 (30%)
        if income > t3:
            b4_slice = min(income, t_sur) - t3
            b4_tax = b4_slice * Decimal("0.30")
            total_tax += b4_tax
        else:
            b4_slice = zero
            b4_tax = zero
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 4 (UGX 485,000 to 10,000,000)",
                lower_limit=t3,
                upper_limit=t_sur,
                taxable_slice=b4_slice,
                rate_percent=Decimal("30.0"),
                tax_amount=b4_tax,
            )
        )

        # Band 5: Above 10,000,000 (30% standard + 10% statutory surcharge = 40% marginal)
        if income > t_sur:
            b5_slice = income - t_sur
            # In Uganda law: 30% of excess over 485k + 10% of excess over 10M.
            # On the excess above 10M, that is (30% + 10%) = 40% total.
            b5_base_tax = b5_slice * Decimal("0.30")
            b5_surcharge = b5_slice * Decimal("0.10")
            b5_tax = b5_base_tax + b5_surcharge
            total_tax += b5_tax
        else:
            b5_slice = zero
            b5_tax = zero
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 5 (Above UGX 10,000,000 - 30% Base + 10% Surcharge)",
                lower_limit=t_sur,
                upper_limit=None,
                taxable_slice=b5_slice,
                rate_percent=Decimal("40.0"),
                tax_amount=b5_tax,
            )
        )

        marginal_rate = self._get_marginal_rate_resident(income)
        effective_rate = (
            (total_tax.amount / income.amount).quantize(Decimal("0.0001"))
            if income > zero
            else Decimal("0.0000")
        )

        return TaxResult(
            tax_payable=total_tax,
            taxable_base=income,
            effective_rate=effective_rate,
            marginal_rate=marginal_rate,
            bands=bands_audit,
            summary=f"Resident PAYE on {income} is {total_tax} (Effective rate: {effective_rate * 100:.2f}%)",
            metadata={"residency": "RESIDENT", "surcharge_applied": income > t_sur},
        )

    def _calculate_non_resident(self, income: Money) -> TaxResult:
        """Calculate non-resident PAYE according to statutory progressive bands."""
        bands_audit: List[TaxBandAudit] = []
        zero = Money.zero()
        t1, t2, t3, t_sur = self.RESIDENT_T1, self.RESIDENT_T2, self.RESIDENT_T3, self.SURCHARGE_THRESHOLD

        total_tax = zero

        # Band 1: Up to 335,000 (10%)
        b1_slice = min(income, t1)
        b1_tax = b1_slice * Decimal("0.10")
        total_tax += b1_tax
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 1 (Up to UGX 335,000)",
                lower_limit=zero,
                upper_limit=t1,
                taxable_slice=b1_slice,
                rate_percent=Decimal("10.0"),
                tax_amount=b1_tax,
            )
        )

        # Band 2: 335,000 to 410,000 (20%)
        if income > t1:
            b2_slice = min(income, t2) - t1
            b2_tax = b2_slice * Decimal("0.20")
            total_tax += b2_tax
        else:
            b2_slice = zero
            b2_tax = zero
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 2 (UGX 335,000 to 410,000)",
                lower_limit=t1,
                upper_limit=t2,
                taxable_slice=b2_slice,
                rate_percent=Decimal("20.0"),
                tax_amount=b2_tax,
            )
        )

        # Band 3: 410,000 to 485,000 (25%)
        if income > t2:
            b3_slice = min(income, t3) - t2
            b3_tax = b3_slice * Decimal("0.25")
            total_tax += b3_tax
        else:
            b3_slice = zero
            b3_tax = zero
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 3 (UGX 410,000 to 485,000)",
                lower_limit=t2,
                upper_limit=t3,
                taxable_slice=b3_slice,
                rate_percent=Decimal("25.0"),
                tax_amount=b3_tax,
            )
        )

        # Band 4: 485,000 to 10,000,000 (30%)
        if income > t3:
            b4_slice = min(income, t_sur) - t3
            b4_tax = b4_slice * Decimal("0.30")
            total_tax += b4_tax
        else:
            b4_slice = zero
            b4_tax = zero
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 4 (UGX 485,000 to 10,000,000)",
                lower_limit=t3,
                upper_limit=t_sur,
                taxable_slice=b4_slice,
                rate_percent=Decimal("30.0"),
                tax_amount=b4_tax,
            )
        )

        # Band 5: Above 10,000,000 (30% + 10% Surcharge = 40%)
        if income > t_sur:
            b5_slice = income - t_sur
            b5_tax = b5_slice * Decimal("0.40")
            total_tax += b5_tax
        else:
            b5_slice = zero
            b5_tax = zero
        bands_audit.append(
            TaxBandAudit(
                band_name="Band 5 (Above UGX 10,000,000 - 30% Base + 10% Surcharge)",
                lower_limit=t_sur,
                upper_limit=None,
                taxable_slice=b5_slice,
                rate_percent=Decimal("40.0"),
                tax_amount=b5_tax,
            )
        )

        marginal_rate = self._get_marginal_rate_non_resident(income)
        effective_rate = (
            (total_tax.amount / income.amount).quantize(Decimal("0.0001"))
            if income > zero
            else Decimal("0.0000")
        )

        return TaxResult(
            tax_payable=total_tax,
            taxable_base=income,
            effective_rate=effective_rate,
            marginal_rate=marginal_rate,
            bands=bands_audit,
            summary=f"Non-Resident PAYE on {income} is {total_tax} (Effective rate: {effective_rate * 100:.2f}%)",
            metadata={"residency": "NON_RESIDENT", "surcharge_applied": income > t_sur},
        )

    def _get_marginal_rate_resident(self, income: Money) -> Decimal:
        if income <= self.RESIDENT_T1:
            return Decimal("0.00")
        elif income <= self.RESIDENT_T2:
            return Decimal("0.20")
        elif income <= self.RESIDENT_T3:
            return Decimal("0.25")
        elif income <= self.SURCHARGE_THRESHOLD:
            return Decimal("0.30")
        else:
            return Decimal("0.40")

    def _get_marginal_rate_non_resident(self, income: Money) -> Decimal:
        if income <= self.RESIDENT_T1:
            return Decimal("0.10")
        elif income <= self.RESIDENT_T2:
            return Decimal("0.20")
        elif income <= self.RESIDENT_T3:
            return Decimal("0.25")
        elif income <= self.SURCHARGE_THRESHOLD:
            return Decimal("0.30")
        else:
            return Decimal("0.40")

