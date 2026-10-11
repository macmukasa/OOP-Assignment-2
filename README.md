# Uganda Tax Engine (Mini-Project 2)
**MSCS & MSDS OOP with Python — Assignment 2 (Advent 2026)**

---

## 1. Project Overview

The **Uganda Tax Engine** is an extensible, mathematically sound, domain-driven software suite that models the statutory direct and indirect tax policies administered by the **Uganda Revenue Authority (URA)** and statutory authorities.

This implementation satisfies all mandatory core requirements and **Extension Task A (Withholding Tax and Rental Income Tax)**.

### Statutory Baselines & Regulatory Citations
1. **Pay As You Earn (PAYE)**:
   - *Uganda Income Tax Act (Cap 340), First Schedule, Part I (Resident Individuals) & Part II (Non-Resident Individuals)*.
   - *Income Tax (Amendment) Act 2012*: Imposition of the 10% statutory surcharge on monthly employment income exceeding UGX 10,000,000.
2. **National Social Security Fund (NSSF)**:
   - *National Social Security Fund Act (Cap 222)*: Mandatory employee contribution of 5% and employer matching contribution of 10% on gross cash remuneration (Total 15%).
3. **Local Service Tax (LST)**:
   - *Local Governments (Amendment) Act 2008* & URA Practice Notes: Statutory municipal tax applied as an allowable pre-tax deduction against employment income before PAYE determination.
4. **Value Added Tax (VAT)**:
   - *Value Added Tax Act (Cap 349)*: Standard rate of 18% (Section 14), Zero-rated supplies (Section 24 & Third Schedule), and Exempt supplies (Section 19 & Second Schedule). Input tax apportionment and non-deductibility for exempt operations (Section 28).
5. **Corporate Income Tax (CIT)**:
   - *Uganda Income Tax Act (Cap 340)*: Standard 30% rate for resident corporate entities on net chargeable income (Gross Turnover less Section 22 allowable deductions and Section 38 loss carryforward relief).
6. **Withholding Tax (WHT - Extension Task A)**:
   - *Uganda Income Tax Act (Cap 340)*:
     - **Section 119**: 6% WHT on commercial supply of goods/materials where transaction value exceeds UGX 1,000,000 (with exemption certificate handling).
     - **Section 119A**: 15% flat WHT on professional, management, legal, and consultancy services.
7. **Individual Rental Income Tax (Extension Task A)**:
   - *Income Tax (Amendment) Act 2022/2023, Section 5(3)*: Flat 12% tax on gross rental income exceeding the statutory threshold of UGX 235,000 monthly (UGX 2,820,000 annually), with zero deductions for expenses or depreciation allowed for individuals.

---

## 2. Repository Structure

```
.
├── project2_uganda_tax_engine.ipynb   # Main Jupyter Notebook (fully executable top-to-bottom)
├── README.md                          # Architecture, findings, setup, and AI declaration
├── requirements.txt                   # Pip dependencies specification
├── environment.yml                    # Conda environment specification (oop2)
├── pytest.ini                         # Pytest configuration
├── src/
│   ├── __init__.py
│   └── tax_engine/
│       ├── __init__.py                # Package exports
│       ├── money.py                   # Immutable Money Value Object in UGX (Decimal only)
│       ├── exceptions.py              # Custom TaxError hierarchy
│       ├── base.py                    # Abstract Tax base class, TaxContext, TaxResult
│       ├── paye.py                    # Resident & Non-Resident progressive PAYE engine
│       ├── payroll.py                 # Comprehensive payroll pipeline (NSSF, LST, Net Pay, CTC)
│       ├── vat.py                     # VAT invoicing engine (Standard, Zero-rated, Exempt)
│       ├── corporate.py               # Corporate income tax, deductions & loss relief
│       └── extensions.py              # Extension Task A: Withholding Tax & Rental Tax
└── tests/
    ├── __init__.py
    ├── test_money.py                  # Money immutability, operator overloading & float rejection
    ├── test_paye_boundaries.py        # Boundary tests at every statutory edge (335k, 410k, 485k, 10M, 10M+1)
    ├── test_hypothesis_properties.py  # Property-based testing with Hypothesis
    ├── test_payroll.py                # Payroll pipeline and deduction ordering
    ├── test_vat.py                    # VAT invoices reconciliation & refund testing
    ├── test_corporate.py              # Corporate assessment & loss carryforwards
    ├── test_extensions.py             # WHT threshold & individual rental tax tests
    └── test_exceptions.py             # Custom exceptions and invalid input prevention
```

---

## 3. Environment Setup & Execution

### Prerequisites
- Python 3.13 or 3.14
- Conda package manager

### Activating the `oop2` Conda Environment
To use the pre-configured environment:
```powershell
conda activate oop2
```
If recreating the environment from scratch:
```powershell
conda env create -f environment.yml
conda activate oop2
```

### Running Automated Tests
Run the entire 61-test test suite via pytest:
```powershell
pytest
```
All 61 tests (including unit, boundary, and Hypothesis property-based tests) pass cleanly without errors.

### Running the Jupyter Notebook
Launch Jupyter:
```powershell
jupyter notebook project2_uganda_tax_engine.ipynb
```
Select the **oop2** kernel. The notebook is deterministic and reproducible (`np.random.default_rng(42)`) and executes from start to finish via **Kernel -> Restart & Run All** with zero errors.

---

## 4. Software Architecture & OOP Design

### Mandatory Design Constraints

#### 1. The `Money` Value Object (`src/tax_engine/money.py`)
- **Strictly rejects `float`**: Passing float values to `Money()` or attempting arithmetic with floats raises explicit `TypeError`s to eliminate binary representation drift.
- **Pure `Decimal` arithmetic**: Amounts are quantized internally using `decimal.ROUND_HALF_UP`.
- **Value Object Immutability**: Protected with `__slots__` and overriding `__setattr__` / `__delattr__`.
- **Operator Overloading**: Implements `__add__`, `__sub__`, `__mul__`, `__truediv__`, `__lt__`, `__le__`, `__gt__`, `__ge__`, `__eq__`, `__ne__`, `__repr__`, `__str__`, `__neg__`, and `__bool__`. Division of `Money / Money` correctly returns a dimensionless `Decimal` ratio.

#### 2. Abstract Base Class `Tax` (`src/tax_engine/base.py`)
- Enforces the abstract contract:
  ```python
  class Tax(ABC):
      @abstractmethod
      def calculate(self, ctx: TaxContext) -> TaxResult:
          ...
  ```
- Subclasses: `PAYETax`, `VATModule`, `CorporateIncomeTax`, `WithholdingTax`, and `RentalIncomeTax`.
- Conforms to the **Liskov Substitution Principle (LSP)**: Any consumer can invoke `.calculate(ctx)` polymorphically.

#### 3. Custom Exception Hierarchy (`src/tax_engine/exceptions.py`)
- Base class: `TaxError(Exception)`.
- Domain exceptions:
  - `InvalidIncomeError`: Raised on negative or unparseable monetary quantities.
  - `NoScheduleForDateError`: Raised when tax date is outside supported statutory years.
  - `CurrencyMismatchError`: Raised when attempting operations between incompatible currencies.
  - `NegativeValueError`: Raised when non-negative amounts are violated.
  - `InvalidSupplyTypeError`: Raised when supply categories are malformed.
  - `TaxValidationError`: Raised on illegal parameter configurations.
- **Never fails silently**: All edge cases, invalid dates, and negative amounts raise explicit domain errors.

---

## 5. Payroll Pipeline: Deduction Hierarchy & Justification

The pipeline implements the following deduction ordering:

```
[Basic Salary + Cash Allowances]
               │
               ▼
       Gross Employment Pay
               │
               ├─► Pre-Tax Deduction: Local Service Tax (LST)
               │   (Justification: Allowed under Local Governments Act / URA practice notes)
               ▼
      Taxable PAYE Base = max(0, Gross - LST)
               │
               ├─► Statutory Progressive Calculation: PAYE Tax
               │   (Resident or Non-Resident bands + 10% surcharge)
               │
               ├─► Statutory Employee Pension: Employee NSSF (5% of Gross)
               │   (Justification: Computed on gross pay under NSSF Act; non-exempt for private PAYE)
               ▼
     Net Take-Home Pay = Gross - Employee NSSF - LST - PAYE
```
**Employer Liability (Cost to Company - CTC)**:
- $\text{Employer NSSF (10%)} = \text{Gross} \times 10\%$
- $\text{Total CTC} = \text{Gross} + \text{Employer NSSF}$

---

## 6. Testing Strategy & Rubric Verification

### Boundary Tests at Band Edges (`tests/test_paye_boundaries.py`)
Verified at all required threshold transitions:
- **UGX 335,000**: Resident Tax = Nil; Non-Resident Tax = UGX 33,500.00.
- **UGX 335,001**: Resident Tax = UGX 0.20 (20% marginal tier begins); Non-Resident = UGX 33,500.20.
- **UGX 410,000**: Resident Tax = UGX 15,000.00; Non-Resident = UGX 48,500.00.
- **UGX 485,000**: Resident Tax = UGX 33,750.00; Non-Resident = UGX 67,250.00.
- **UGX 10,000,000**: Resident Tax = UGX 2,888,250.00; Non-Resident = UGX 2,921,750.00.
- **UGX 10,000,001**: Resident Tax = UGX 2,888,250.40 (40% marginal rate begins); Non-Resident = UGX 2,921,750.40.

### Hypothesis Property-Based Testing (`tests/test_hypothesis_properties.py`)
1. **Non-negativity**: $\forall x \ge 0, \text{tax}(x) \ge 0$.
2. **Monotonicity**: $x_1 \le x_2 \implies \text{tax}(x_1) \le \text{tax}(x_2)$.
3. **Upper Bound**: $\forall x \ge 0, \text{tax}(x) \le x$.
4. **Residency Dominance**: $\forall x \ge 0, \text{tax}_{\text{non-res}}(x) \ge \text{tax}_{\text{res}}(x)$.
5. **Take-Home Monotonicity**: $x_1 \le x_2 \implies (x_1 - \text{tax}(x_1)) \le (x_2 - \text{tax}(x_2))$ (no 100%+ marginal cliff).

---

## 7. Discussion Questions & Analysis

### Q1: Why is `float` unsafe for tax computation?
Binary floating-point numbers represent values using powers of two ($2^{-n}$), which cannot exactly represent base-10 decimals like $0.1$ or $0.2$. In tax systems, this produces:
1. **Threshold Discrepancies**: In floats, `335000.10 + 0.20 > 335000.30` evaluates to `True` due to representation error ($335000.300000000035$), erroneously classifying a taxpayer into a higher tax bracket.
2. **Cumulative Financial Drift**: Reconciling 100,000 invoice line items or employee payroll records causes rounding truncation that accumulates into substantial financial drift, failing statutory URA audits.
3. **Non-deterministic Rounding**: Floats default to round-half-to-even without explicit rounding control, violating legal rounding conventions (such as `ROUND_HALF_UP`).

### Q2: Where was inheritance justified, and where was it deliberately avoided?
- **Justified**:
  - `Tax(ABC)` base class: Polymorphic calculate contract adhered to by `PAYETax`, `VATModule`, `CorporateIncomeTax`, `WithholdingTax`, and `RentalIncomeTax`. Satisfies LSP.
  - `TaxError(Exception)` hierarchy: Enables clean domain exception filtering.
- **Deliberately Avoided**:
  - `Money` does **not** inherit from `Decimal`. It encapsulates `Decimal` via composition and slots to prevent unwanted mathematical methods (e.g. `sqrt`, `exp`) and maintain strict currency and float guards.
  - `PayrollPipeline` does **not** inherit from `Tax`. A payroll system is an orchestration workflow composing multiple taxes and deductions, not a tax itself.

---

## 8. Academic Integrity & AI Declaration

In accordance with course academic integrity regulations, this project was developed with assistance from the AI coding assistant **Antigravity** (Google DeepMind).

### Scope of AI Assistance
- **Domain Modeling & Scaffolding**: Drafting initial class signatures and docstrings based on the URA regulatory baseline.
- **Test Generation**: Assisting with boundary test matrices and Hypothesis property strategies.
- **Visualization Scripts**: Structuring multi-panel Matplotlib figures with proper axis labels and formatting.

All regulatory rules, mathematical formulas, and code logic were reviewed, validated against official URA statutory documents, and verified through an automated 61-test suite. The author is fully prepared to explain and defend every component of the code during the viva examination.

