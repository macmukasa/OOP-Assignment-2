"""Uganda Tax Engine: A domain-driven, extensible tax calculation suite.

Models tax policies under the Uganda Revenue Authority (URA):
- PAYE (Resident and Non-Resident monthly progressive bands with surcharge)
- Payroll pipeline (NSSF, Local Service Tax, PAYE, Net Pay, CTC)
- Value Added Tax (Standard, Zero-rated, Exempt supplies)
- Corporate Income Tax (30% resident CIT, deductions, loss carryforward)
- Withholding Tax (ITA Section 119/119A: 6% on goods > 1M, 15% on professional fees)
- Rental Income Tax (ITA Amendment 2022/2023: 12% on individual gross rent over threshold)
"""

from .money import Money
from .exceptions import (
    TaxError,
    InvalidIncomeError,
    NoScheduleForDateError,
    CurrencyMismatchError,
    NegativeValueError,
    InvalidSupplyTypeError,
    TaxValidationError,
)
from .base import (
    Tax,
    TaxContext,
    TaxResult,
    TaxBandAudit,
    ResidencyStatus,
)
from .paye import PAYETax
from .payroll import PayrollPipeline, PayrollSlip
from .vat import (
    VATModule,
    SupplyType,
    InvoiceType,
    InvoiceLine,
    Invoice,
    VATReturnSummary,
)
from .corporate import CorporateIncomeTax, CorporateAssessment
from .extensions import (
    WithholdingTax,
    WHTCategory,
    WHTResult,
    RentalIncomeTax,
    RentalTaxResult,
)

__all__ = [
    "Money",
    "TaxError",
    "InvalidIncomeError",
    "NoScheduleForDateError",
    "CurrencyMismatchError",
    "NegativeValueError",
    "InvalidSupplyTypeError",
    "TaxValidationError",
    "Tax",
    "TaxContext",
    "TaxResult",
    "TaxBandAudit",
    "ResidencyStatus",
    "PAYETax",
    "PayrollPipeline",
    "PayrollSlip",
    "VATModule",
    "SupplyType",
    "InvoiceType",
    "InvoiceLine",
    "Invoice",
    "VATReturnSummary",
    "CorporateIncomeTax",
    "CorporateAssessment",
    "WithholdingTax",
    "WHTCategory",
    "WHTResult",
    "RentalIncomeTax",
    "RentalTaxResult",
]

