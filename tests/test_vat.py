"""Unit tests for Value Added Tax (VAT) module."""

import pytest
from decimal import Decimal
from src.tax_engine.money import Money
from src.tax_engine.vat import (
    VATModule,
    SupplyType,
    InvoiceType,
    InvoiceLine,
    Invoice,
)
from src.tax_engine.base import TaxContext
from src.tax_engine.exceptions import InvalidIncomeError


@pytest.fixture
def vat_engine() -> VATModule:
    return VATModule()


def test_vat_standard_supply_calculation(vat_engine: VATModule):
    # 18% standard rate on 1,000,000 UGX
    ctx = TaxContext(gross_amount=Money("1000000"))
    result = vat_engine.calculate(ctx)

    assert result.tax_payable == Money("180000.00")
    assert result.effective_rate == Decimal("0.18")
    assert result.marginal_rate == Decimal("0.18")


def test_invoice_lines():
    line_std = InvoiceLine(
        description="Consulting services",
        net_amount=Money("1000000"),
        supply_type=SupplyType.STANDARD_RATED,
    )
    assert line_std.vat_rate == Decimal("0.18")
    assert line_std.vat_amount == Money("180000.00")
    assert line_std.gross_amount == Money("1180000.00")

    line_zero = InvoiceLine(
        description="Coffee exports",
        net_amount=Money("2000000"),
        supply_type=SupplyType.ZERO_RATED,
    )
    assert line_zero.vat_rate == Decimal("0.00")
    assert line_zero.vat_amount == Money.zero()
    assert line_zero.gross_amount == Money("2000000.00")

    line_exempt = InvoiceLine(
        description="Bank loan interest",
        net_amount=Money("500000"),
        supply_type=SupplyType.EXEMPT,
    )
    assert line_exempt.vat_rate == Decimal("0.00")
    assert line_exempt.vat_amount == Money.zero()
    assert line_exempt.gross_amount == Money("500000.00")


def test_vat_invoice_reconciliation_payable(vat_engine: VATModule):
    # Sales Invoice:
    # 1. Standard sales: 10,000,000 UGX -> Output VAT 1,800,000
    # 2. Export sales (zero-rated): 5,000,000 UGX -> Output VAT 0
    # 3. Exempt sales: 2,000,000 UGX -> Output VAT 0
    sales_inv = Invoice(
        invoice_number="INV-001",
        invoice_type=InvoiceType.SALES,
        party_name="Kampala Traders Ltd",
        lines=[
            InvoiceLine("Standard products", Money("10000000"), SupplyType.STANDARD_RATED),
            InvoiceLine("Export goods", Money("5000000"), SupplyType.ZERO_RATED),
            InvoiceLine("Agricultural produce", Money("2000000"), SupplyType.EXEMPT),
        ],
    )

    # Purchase Invoice:
    # 1. Raw materials (standard): 4,000,000 UGX -> Claimable input VAT = 720,000
    # 2. Financial service fees (exempt): 1,000,000 UGX -> Non-claimable
    purchase_inv = Invoice(
        invoice_number="PUR-001",
        invoice_type=InvoiceType.PURCHASE,
        party_name="Raw Materials Co",
        lines=[
            InvoiceLine("Factory raw materials", Money("4000000"), SupplyType.STANDARD_RATED),
            InvoiceLine("Banking charges", Money("1000000"), SupplyType.EXEMPT),
        ],
    )

    summary = vat_engine.process_invoices([sales_inv, purchase_inv])

    assert summary.output_vat == Money("1800000.00")
    assert summary.claimable_input_vat == Money("720000.00")
    # Net VAT Payable = 1,800,000 - 720,000 = 1,080,000 UGX
    assert summary.net_vat_payable == Money("1080000.00")
    assert not summary.is_credit


def test_vat_credit_scenario(vat_engine: VATModule):
    # Sales: 1,000,000 UGX standard -> Output VAT = 180,000
    # Purchases: 3,000,000 UGX standard -> Input VAT = 540,000
    sales_inv = Invoice(
        invoice_number="INV-002",
        invoice_type=InvoiceType.SALES,
        party_name="Local Client",
        lines=[InvoiceLine("Retail Goods", Money("1000000"), SupplyType.STANDARD_RATED)],
    )
    purch_inv = Invoice(
        invoice_number="PUR-002",
        invoice_type=InvoiceType.PURCHASE,
        party_name="Machinery Supplier",
        lines=[InvoiceLine("Heavy Equipment", Money("3000000"), SupplyType.STANDARD_RATED)],
    )

    summary = vat_engine.process_invoices([sales_inv, purch_inv])
    # Net VAT = 180,000 - 540,000 = -360,000 (credit)
    assert summary.net_vat_payable == Money("-360000.00")
    assert summary.is_credit

