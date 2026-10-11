"""Value Added Tax (VAT) module for Uganda.

Implements statutory VAT processing under the Uganda Value Added Tax Act (Cap 349):
- Standard rate: 18%
- Zero-rated supplies: 0% (input VAT claimable)
- Exempt supplies: No VAT charged (input VAT non-claimable per VAT Act Section 28)

Computes output VAT, allowable input VAT credits, and net VAT payable or refundable.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from .money import Money
from .exceptions import InvalidIncomeError, InvalidSupplyTypeError
from .base import Tax, TaxContext, TaxResult


class SupplyType(str, Enum):
    """Statutory VAT classification of supplies."""
    STANDARD_RATED = "STANDARD_RATED"  # 18% standard rate
    ZERO_RATED = "ZERO_RATED"          # 0% rate (exports, essential medical, etc.)
    EXEMPT = "EXEMPT"                  # No tax; input tax non-creditable


class InvoiceType(str, Enum):
    """Type of transaction invoice."""
    SALES = "SALES"        # Outward supplies generating Output VAT
    PURCHASE = "PURCHASE"  # Inward supplies generating potential Input VAT credit


@dataclass(frozen=True)
class InvoiceLine:
    """Individual line item on a VAT invoice."""
    description: str
    net_amount: Money
    supply_type: SupplyType = SupplyType.STANDARD_RATED

    def __post_init__(self) -> None:
        if self.net_amount.is_negative():
            raise InvalidIncomeError(f"Invoice line amount cannot be negative: {self.net_amount}")
        if not isinstance(self.supply_type, SupplyType):
            raise InvalidSupplyTypeError(f"Invalid supply type: {self.supply_type}")

    @property
    def vat_rate(self) -> Decimal:
        """Return the VAT rate applicable to this supply type."""
        if self.supply_type == SupplyType.STANDARD_RATED:
            return Decimal("0.18")
        return Decimal("0.00")

    @property
    def vat_amount(self) -> Money:
        """Compute the VAT charged on this line."""
        return self.net_amount * self.vat_rate

    @property
    def gross_amount(self) -> Money:
        """Gross amount including VAT."""
        return self.net_amount + self.vat_amount


@dataclass(frozen=True)
class Invoice:
    """Tax invoice containing one or more line items."""
    invoice_number: str
    invoice_type: InvoiceType
    party_name: str
    lines: List[InvoiceLine] = field(default_factory=list)

    @property
    def net_total(self) -> Money:
        return sum((line.net_amount for line in self.lines), Money.zero())

    @property
    def vat_total(self) -> Money:
        return sum((line.vat_amount for line in self.lines), Money.zero())

    @property
    def gross_total(self) -> Money:
        return self.net_total + self.vat_total

    @property
    def claimable_vat(self) -> Money:
        """Determine claimable input VAT.

        Per Section 28 of Uganda VAT Act, input tax incurred on purchases
        directly allocated to making exempt supplies is non-deductible.
        Only VAT on standard and zero-rated purchases is claimable.
        """
        if self.invoice_type != InvoiceType.PURCHASE:
            return Money.zero()
        # Only lines with standard-rated supplies have VAT to claim
        return sum(
            (line.vat_amount for line in self.lines if line.supply_type == SupplyType.STANDARD_RATED),
            Money.zero(),
        )


@dataclass(frozen=True)
class VATReturnSummary:
    """Complete statutory VAT Return filing summary."""
    standard_sales: Money
    zero_rated_sales: Money
    exempt_sales: Money
    total_sales: Money
    output_vat: Money
    claimable_input_vat: Money
    non_claimable_exempt_input_vat: Money
    total_purchases: Money
    net_vat_payable: Money
    is_credit: bool
    invoice_count: int


class VATModule(Tax):
    """Uganda Value Added Tax Engine conforming to the abstract Tax contract."""

    STANDARD_RATE = Decimal("0.18")

    def __init__(self) -> None:
        super().__init__(
            name="Uganda VAT Module",
            description="Computes Output VAT, Input VAT credits, and Net VAT liability under Cap 349",
        )

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Implements abstract Tax contract for standard taxable sales base."""
        if ctx.gross_amount.is_negative():
            raise InvalidIncomeError(f"Taxable turnover cannot be negative: {ctx.gross_amount}")

        tax_amount = ctx.gross_amount * self.STANDARD_RATE
        return TaxResult(
            tax_payable=tax_amount,
            taxable_base=ctx.gross_amount,
            effective_rate=self.STANDARD_RATE,
            marginal_rate=self.STANDARD_RATE,
            summary=f"Output VAT on standard taxable supplies of {ctx.gross_amount} is {tax_amount}",
            metadata={"supply_type": "STANDARD_RATED", "rate": "18%"},
        )

    def process_invoices(self, invoices: List[Invoice]) -> VATReturnSummary:
        """Process a collection of sales and purchase invoices for a tax period.

        Returns:
            VATReturnSummary with audit reconciliations of Output VAT,
            Input VAT credits, and Net VAT payable/credit.
        """
        std_sales = Money.zero()
        zero_sales = Money.zero()
        exempt_sales = Money.zero()
        output_vat = Money.zero()

        purchases_total = Money.zero()
        claimable_input_vat = Money.zero()
        non_claimable_input_vat = Money.zero()

        for inv in invoices:
            if inv.invoice_type == InvoiceType.SALES:
                for line in inv.lines:
                    if line.supply_type == SupplyType.STANDARD_RATED:
                        std_sales += line.net_amount
                        output_vat += line.vat_amount
                    elif line.supply_type == SupplyType.ZERO_RATED:
                        zero_sales += line.net_amount
                    elif line.supply_type == SupplyType.EXEMPT:
                        exempt_sales += line.net_amount
            elif inv.invoice_type == InvoiceType.PURCHASE:
                for line in inv.lines:
                    purchases_total += line.net_amount
                    if line.supply_type == SupplyType.STANDARD_RATED:
                        claimable_input_vat += line.vat_amount
                    elif line.supply_type == SupplyType.EXEMPT:
                        # Exempt purchases bear no VAT, but any VAT attached to exempt operations is disallowed
                        pass

        total_sales = std_sales + zero_sales + exempt_sales
        net_liability = output_vat - claimable_input_vat
        is_credit = net_liability.is_negative()

        return VATReturnSummary(
            standard_sales=std_sales,
            zero_rated_sales=zero_sales,
            exempt_sales=exempt_sales,
            total_sales=total_sales,
            output_vat=output_vat,
            claimable_input_vat=claimable_input_vat,
            non_claimable_exempt_input_vat=non_claimable_input_vat,
            total_purchases=purchases_total,
            net_vat_payable=net_liability,
            is_credit=is_credit,
            invoice_count=len(invoices),
        )

