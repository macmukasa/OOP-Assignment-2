"""Abstract base classes and core data contracts for the Uganda Tax Engine.

Defines the contract for tax calculation:
    Tax.calculate(ctx: TaxContext) -> TaxResult
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from .money import Money
from .exceptions import InvalidIncomeError


class ResidencyStatus(str, Enum):
    """Residency status under the Uganda Income Tax Act."""
    RESIDENT = "RESIDENT"
    NON_RESIDENT = "NON_RESIDENT"


@dataclass(frozen=True)
class TaxContext:
    """Input context for a tax calculation.

    Attributes:
        gross_amount: Primary monetary amount subject to tax evaluation.
        allowances: Additional cash or non-cash allowances (e.g. for PAYE).
        residency: Residency status (defaults to RESIDENT).
        effective_date: Applicable tax date for schedule lookup.
        metadata: Extra contextual key-value pairs.
    """
    gross_amount: Money
    allowances: Money = field(default_factory=Money.zero)
    residency: ResidencyStatus = ResidencyStatus.RESIDENT
    effective_date: Optional[date] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.gross_amount.is_negative():
            raise InvalidIncomeError(f"Gross amount cannot be negative: {self.gross_amount}")
        if self.allowances.is_negative():
            raise InvalidIncomeError(f"Allowances cannot be negative: {self.allowances}")


@dataclass(frozen=True)
class TaxBandAudit:
    """Audit record for a single progressive tax band."""
    band_name: str
    lower_limit: Money
    upper_limit: Optional[Money]
    taxable_slice: Money
    rate_percent: Decimal
    tax_amount: Money


@dataclass(frozen=True)
class TaxResult:
    """Detailed result of a tax calculation.

    Attributes:
        tax_payable: Net tax liability in UGX.
        taxable_base: The base amount upon which tax was calculated.
        effective_rate: Ratio of tax_payable to taxable_base (0.00 to 1.00).
        marginal_rate: Marginal tax rate applicable to the highest unit of income.
        bands: Itemized breakdown of tax computed per progressive tier.
        summary: Narrative description of the tax calculation result.
        metadata: Additional engine-specific outputs.
    """
    tax_payable: Money
    taxable_base: Money
    effective_rate: Decimal
    marginal_rate: Decimal
    bands: List[TaxBandAudit] = field(default_factory=list)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class Tax(ABC):
    """Abstract Base Class for all tax types in the Uganda Tax Engine."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate tax liability for the provided context.

        Args:
            ctx: TaxContext containing amounts, residency, and date.

        Returns:
            TaxResult containing tax payable, effective rate, and band breakdown.

        Raises:
            TaxError: If calculation parameters are invalid or schedules missing.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

