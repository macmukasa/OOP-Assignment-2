"""Extension Modules for the Uganda Tax Engine: Withholding Tax and Rental Income Tax.

Regulatory Baselines:
1. Withholding Tax (WHT):
   - Section 119, Uganda Income Tax Act (Cap 340): 6% on commercial supply of goods
     and materials where transaction value exceeds UGX 1,000,000.
   - Section 119A, Uganda Income Tax Act: 15% on professional, management, technical,
     or consultancy service fees.
2. Individual Rental Income Tax:
   - Income Tax (Amendment) Act 2022/2023 (Section 5(3)): Flat 12% rate on gross rental
     income exceeding the statutory threshold of UGX 2,820,000 per annum
     (UGX 235,000 monthly). No expense or depreciation deductions are allowed for individuals.
"""

from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional
from .money import Money
from .exceptions import InvalidIncomeError
from .base import Tax, TaxContext, TaxResult


class WHTCategory(str, Enum):
    """Statutory Withholding Tax transaction categories."""
    GOODS_AND_SERVICES = "GOODS_AND_SERVICES"  # 6% rate, subject to UGX 1,000,000 threshold
    PROFESSIONAL_FEES = "PROFESSIONAL_FEES"    # 15% rate on professional/consultancy services


@dataclass(frozen=True)
class WHTResult:
    """Detailed outcome of a withholding tax evaluation."""
    gross_amount: Money
    category: WHTCategory
    rate_percent: Decimal
    threshold_applicable: Money
    wht_withheld: Money
    net_payable_to_vendor: Money
    exemption_applied: bool
    summary: str


class WithholdingTax(Tax):
    """Uganda Withholding Tax (WHT) Calculator."""

    GOODS_THRESHOLD = Money(Decimal("1000000"), round_cents=False)
    RATE_GOODS = Decimal("0.06")
    RATE_PROFESSIONAL = Decimal("0.15")

    def __init__(self) -> None:
        super().__init__(
            name="Uganda Withholding Tax",
            description="6% on goods (> 1M UGX) and 15% on professional fees under ITA Sections 119 and 119A",
        )

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Abstract Tax contract implementation (defaults to goods/services or metadata category)."""
        category_str = ctx.metadata.get("category", WHTCategory.GOODS_AND_SERVICES)
        category = WHTCategory(category_str) if isinstance(category_str, str) else category_str
        has_exemption = ctx.metadata.get("has_exemption", False)

        res = self.withhold(ctx.gross_amount, category=category, has_exemption=has_exemption)

        return TaxResult(
            tax_payable=res.wht_withheld,
            taxable_base=ctx.gross_amount,
            effective_rate=(
                (res.wht_withheld.amount / ctx.gross_amount.amount).quantize(Decimal("0.0001"))
                if ctx.gross_amount > Money.zero()
                else Decimal("0.0000")
            ),
            marginal_rate=res.rate_percent / Decimal("100"),
            summary=res.summary,
            metadata={
                "category": category.value,
                "net_payable": str(res.net_payable_to_vendor),
                "exemption": has_exemption,
            },
        )

    def withhold(
        self,
        gross_amount: Money,
        category: WHTCategory = WHTCategory.GOODS_AND_SERVICES,
        has_exemption: bool = False,
    ) -> WHTResult:
        """Evaluate withholding tax deduction for a payment to a resident supplier.

        Args:
            gross_amount: Invoice / contract gross payable in UGX.
            category: WHTCategory (GOODS_AND_SERVICES or PROFESSIONAL_FEES).
            has_exemption: True if supplier holds a valid URA WHT exemption certificate.

        Returns:
            WHTResult detailing amount withheld and net payable.
        """
        if gross_amount.is_negative():
            raise InvalidIncomeError(f"Payment amount cannot be negative: {gross_amount}")

        zero = Money.zero()

        if has_exemption:
            return WHTResult(
                gross_amount=gross_amount,
                category=category,
                rate_percent=Decimal("0.0"),
                threshold_applicable=zero,
                wht_withheld=zero,
                net_payable_to_vendor=gross_amount,
                exemption_applied=True,
                summary=f"No WHT withheld on {gross_amount} due to valid URA exemption certificate.",
            )

        if category == WHTCategory.GOODS_AND_SERVICES:
            # Section 119: Only applies if transaction exceeds UGX 1,000,000
            if gross_amount > self.GOODS_THRESHOLD:
                tax = gross_amount * self.RATE_GOODS
                net = gross_amount - tax
                summary = f"6% WHT ({tax}) withheld on goods/services payment of {gross_amount} (exceeds threshold)."
                rate = Decimal("6.0")
            else:
                tax = zero
                net = gross_amount
                summary = f"Nil WHT on goods/services payment of {gross_amount} (does not exceed threshold of {self.GOODS_THRESHOLD})."
                rate = Decimal("0.0")

            return WHTResult(
                gross_amount=gross_amount,
                category=category,
                rate_percent=rate,
                threshold_applicable=self.GOODS_THRESHOLD,
                wht_withheld=tax,
                net_payable_to_vendor=net,
                exemption_applied=False,
                summary=summary,
            )

        elif category == WHTCategory.PROFESSIONAL_FEES:
            # Section 119A: 15% flat on professional fees with no lower statutory threshold
            tax = gross_amount * self.RATE_PROFESSIONAL
            net = gross_amount - tax
            return WHTResult(
                gross_amount=gross_amount,
                category=category,
                rate_percent=Decimal("15.0"),
                threshold_applicable=zero,
                wht_withheld=tax,
                net_payable_to_vendor=net,
                exemption_applied=False,
                summary=f"15% WHT ({tax}) withheld on professional fees of {gross_amount}.",
            )
        else:
            raise ValueError(f"Unsupported WHT category: {category}")


@dataclass(frozen=True)
class RentalTaxResult:
    """Detailed rental tax calculation result for an individual landlord."""
    gross_rent: Money
    threshold: Money
    taxable_rent: Money
    tax_rate: Decimal
    tax_payable: Money
    net_rental_income: Money
    effective_rate: Decimal
    is_annual: bool
    summary: str


class RentalIncomeTax(Tax):
    """Uganda Individual Rental Income Tax Calculator.

    Cites:
        - Income Tax (Amendment) Act 2022/2023, Section 5(3).
        - 12% flat rate on gross rent exceeding UGX 235,000 monthly (UGX 2,820,000 annual).
        - No allowable expenses or depreciation deductions permitted for individuals.
    """

    MONTHLY_THRESHOLD = Money(Decimal("235000"), round_cents=False)
    ANNUAL_THRESHOLD = Money(Decimal("2820000"), round_cents=False)
    STATUTORY_RATE = Decimal("0.12")

    def __init__(self, is_annual: bool = False) -> None:
        super().__init__(
            name="Uganda Individual Rental Income Tax",
            description="12% tax on gross rent exceeding statutory threshold (Section 5(3) ITA Amendment)",
        )
        self.is_annual = is_annual

    @property
    def threshold(self) -> Money:
        return self.ANNUAL_THRESHOLD if self.is_annual else self.MONTHLY_THRESHOLD

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate rental income tax conforming to abstract Tax contract."""
        res = self.assess_individual(ctx.gross_amount, is_annual=self.is_annual)

        return TaxResult(
            tax_payable=res.tax_payable,
            taxable_base=res.taxable_rent,
            effective_rate=res.effective_rate,
            marginal_rate=self.STATUTORY_RATE if res.gross_rent > self.threshold else Decimal("0.00"),
            summary=res.summary,
            metadata={
                "gross_rent": str(res.gross_rent),
                "threshold": str(res.threshold),
                "net_rental_income": str(res.net_rental_income),
                "is_annual": self.is_annual,
            },
        )

    def assess_individual(self, gross_rent: Money, is_annual: Optional[bool] = None) -> RentalTaxResult:
        """Assess individual rental income tax.

        Args:
            gross_rent: Total gross rental revenue received in UGX.
            is_annual: Whether the period is annual (UGX 2.82M threshold) or monthly (UGX 235k).

        Returns:
            RentalTaxResult detailing taxable rent, tax liability, and net rent.
        """
        if gross_rent.is_negative():
            raise InvalidIncomeError(f"Gross rent cannot be negative: {gross_rent}")

        annual_mode = self.is_annual if is_annual is None else is_annual
        threshold = self.ANNUAL_THRESHOLD if annual_mode else self.MONTHLY_THRESHOLD
        zero = Money.zero()

        if gross_rent > threshold:
            taxable_rent = gross_rent - threshold
            tax_payable = taxable_rent * self.STATUTORY_RATE
        else:
            taxable_rent = zero
            tax_payable = zero

        net_rent = gross_rent - tax_payable
        effective_rate = (
            (tax_payable.amount / gross_rent.amount).quantize(Decimal("0.0001"))
            if gross_rent > zero
            else Decimal("0.0000")
        )

        period_desc = "annual" if annual_mode else "monthly"
        summary = (
            f"Individual rental tax ({period_desc}) on gross rent of {gross_rent} is {tax_payable} "
            f"(Taxable slice over threshold {threshold}: {taxable_rent}, Net rent: {net_rent})."
        )

        return RentalTaxResult(
            gross_rent=gross_rent,
            threshold=threshold,
            taxable_rent=taxable_rent,
            tax_rate=self.STATUTORY_RATE,
            tax_payable=tax_payable,
            net_rental_income=net_rent,
            effective_rate=effective_rate,
            is_annual=annual_mode,
            summary=summary,
        )

