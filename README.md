# Uganda tax engine (mini-project 2)
MSCS & MSDS OOP with Python, Advent 2026

---

## 1. Project overview

The Uganda tax engine is an object-oriented tax calculator that implements the statutory tax rules administered by the Uganda Revenue Authority (URA).

The engine supports all core project specifications and Extension Task A (withholding tax and individual rental income tax).

### Statutory baselines and regulatory citations
- Pay As You Earn (PAYE): Income Tax Act, Cap 340, First Schedule. Resident monthly progressive rates apply: Nil up to UGX 335,000; 20% on excess over 335,000 up to 410,000; 25% on excess over 410,000 up to 485,000; 30% on excess over 485,000 up to 10,000,000. An additional 10% surcharge applies on income exceeding UGX 10,000,000 per the Income Tax (Amendment) Act 2012. Non-residents pay 10% on their initial UGX 335,000 before proceeding to the higher marginal brackets.
- National Social Security Fund (NSSF): NSSF Act, Cap 222 mandates an employee deduction of 5% and an employer matching contribution of 10% on gross cash remuneration.
- Local Service Tax (LST): Local Governments (Amendment) Act 2008 sets a statutory municipal deduction applied to employment income before PAYE determination.
- Value Added Tax (VAT): Value Added Tax Act, Cap 349 sets an 18% standard rate. Zero-rated supplies incur 0% VAT while retaining input tax recovery rights. Exempt supplies incur no output VAT and disallow input tax deduction under Section 28.
- Corporate Income Tax (CIT): Income Tax Act, Cap 340, Sections 22 and 38 set a 30% rate on resident corporate chargeable income, calculated as gross turnover less allowable deductions and assessed loss relief.
- Withholding Tax (WHT): Section 119 sets a 6% deduction on commercial goods supplies above UGX 1,000,000. Section 119A sets a 15% deduction on professional and consultancy fees.
- Individual Rental Income Tax: Section 5(3) of the Income Tax (Amendment) Act 2022/2023 sets a flat 12% rate on gross rent exceeding UGX 235,000 monthly (UGX 2,820,000 annually), with zero deductions allowed for individuals.

---

## 2. Repository structure

```
.
├── project2_uganda_tax_engine.ipynb   # Main Jupyter notebook (runs top-to-bottom)
├── README.md                          # Architecture, findings, setup, and AI declaration
├── requirements.txt                   # Pip package dependencies
├── environment.yml                    # Conda environment specification (oop2)
├── pytest.ini                         # Pytest configuration
├── src/
│   ├── __init__.py
│   └── tax_engine/
│       ├── __init__.py                # Package exports
│       ├── money.py                   # Immutable Money value object in UGX
│       ├── exceptions.py              # TaxError exception hierarchy
│       ├── base.py                    # Abstract Tax class, TaxContext, TaxResult
│       ├── paye.py                    # Progressive PAYE engine
│       ├── payroll.py                 # Payroll pipeline (NSSF, LST, net pay, CTC)
│       ├── vat.py                     # VAT invoicing engine
│       ├── corporate.py               # Corporate income tax, deductions, and loss relief
│       └── extensions.py              # Extension task A: withholding tax and rental tax
└── tests/
    ├── __init__.py
    ├── test_money.py                  # Money immutability, operators, and float rejection
    ├── test_paye_boundaries.py        # Boundary tests at every statutory edge
    ├── test_hypothesis_properties.py  # Property-based testing with Hypothesis
    ├── test_payroll.py                # Payroll pipeline and deduction ordering
    ├── test_vat.py                    # VAT invoices reconciliation and credit tests
    ├── test_corporate.py              # Corporate assessment and loss carryforwards
    ├── test_extensions.py             # WHT threshold and rental tax tests
    └── test_exceptions.py             # Custom exceptions and input validation
```

---

## 3. Environment setup and execution

### Prerequisites
Python 3.13 or 3.14 with the Conda package manager.

### Activating the `oop2` conda environment
To activate the environment:
```powershell
conda activate oop2
```
To recreate the environment:
```powershell
conda env create -f environment.yml
conda activate oop2
```

### Running automated tests
Run the 61-test suite with pytest:
```powershell
pytest
```
All unit, boundary, and property-based tests pass.

### Running the Jupyter notebook
Launch Jupyter:
```powershell
jupyter notebook project2_uganda_tax_engine.ipynb
```
Select the `oop2` kernel. The notebook contains a fixed random seed (`np.random.default_rng(42)`) and executes from start to finish via Kernel -> Restart & Run All without errors.

---

## 4. Software architecture and object-oriented design

### Mandatory design constraints

The `Money` class in `src/tax_engine/money.py` represents monetary values in Ugandan Shillings (UGX). It wraps `decimal.Decimal` with explicit `ROUND_HALF_UP` rounding. Floating-point numbers are rejected during instantiation and arithmetic operations to prevent binary representation drift. Immutability is enforced using `__slots__` and frozen attribute setters. Operator overloading covers addition, subtraction, multiplication, division, and comparisons. Division of two `Money` instances returns a dimensionless `Decimal` ratio.

The abstract base class `Tax` in `src/tax_engine/base.py` defines the calculation interface:
```python
class Tax(ABC):
    @abstractmethod
    def calculate(self, ctx: TaxContext) -> TaxResult:
        ...
```
Concrete subclasses include `PAYETax`, `VATModule`, `CorporateIncomeTax`, `WithholdingTax`, and `RentalIncomeTax`. Each subclass adheres to the Liskov Substitution Principle and supports polymorphic evaluation across tax types.

The exception hierarchy in `src/tax_engine/exceptions.py` roots in `TaxError(Exception)`. Domain-specific subclasses include `InvalidIncomeError`, `NoScheduleForDateError`, `CurrencyMismatchError`, `NegativeValueError`, `InvalidSupplyTypeError`, and `TaxValidationError`. The engine raises explicit exceptions on invalid inputs and unsupported schedules without silent failure.

---

## 5. Payroll pipeline: deduction hierarchy and justification

The payroll pipeline applies deductions in the following sequence:

```
[Basic Salary + Cash Allowances]
               │
               ▼
       Gross Employment Pay
               │
               ├─► Pre-tax deduction: Local Service Tax (LST)
               │   (Justification: Allowed under Local Governments Act and URA guidelines)
               ▼
      Taxable PAYE Base = max(0, Gross - LST)
               │
               ├─► Progressive calculation: PAYE Tax
               │   (Resident or non-resident bands plus 10% surcharge)
               │
               ├─► Employee retirement contribution: Employee NSSF (5% of Gross)
               │   (Justification: Computed on gross pay under NSSF Act; non-exempt for PAYE)
               ▼
     Net Take-Home Pay = Gross - Employee NSSF - LST - PAYE
```

Employer cost to company (CTC) adds the statutory 10% employer NSSF contribution to gross pay:
$$\text{Total CTC} = \text{Gross} + \text{Employer NSSF}$$

---

## 6. Testing strategy and verification

### Boundary tests at band edges
The test suite in `tests/test_paye_boundaries.py` evaluates every statutory band edge:
- 335,000 UGX: Resident tax is nil; non-resident tax is UGX 33,500.00.
- 335,001 UGX: Resident tax is UGX 0.20; non-resident tax is UGX 33,500.20.
- 410,000 UGX: Resident tax is UGX 15,000.00; non-resident tax is UGX 48,500.00.
- 485,000 UGX: Resident tax is UGX 33,750.00; non-resident tax is UGX 67,250.00.
- 10,000,000 UGX: Resident tax is UGX 2,888,250.00; non-resident tax is UGX 2,921,750.00.
- 10,000,001 UGX: Resident tax is UGX 2,888,250.40; non-resident tax is UGX 2,921,750.40.

### Property-based testing with hypothesis
Tests in `tests/test_hypothesis_properties.py` evaluate domain properties across randomized income inputs:
1. Non-negativity: tax liability is non-negative for all non-negative incomes.
2. Monotonicity: higher income never produces lower tax liability.
3. Upper bound: tax liability does not exceed gross income.
4. Residency dominance: non-resident tax liability is greater than or equal to resident tax liability.
5. Take-home monotonicity: net take-home pay increases monotonically with gross pay.

---

## 7. Discussion questions and analysis

### Question 1: why float is unsafe for tax computation
Binary floating-point numbers represent values using powers of two, which cannot represent base-10 decimals like 0.1 or 0.2 exactly. In tax calculation software, this causes three problems:
1. Comparison operations fail at statutory thresholds. The expression `335000.10 + 0.20 > 335000.30` evaluates to `True` in Python floats. This pushes income into a higher tax bracket.
2. Micro-transaction rounding errors accumulate over large transaction volumes and produce financial audit discrepancies.
3. Floating-point numbers lack deterministic control over regulatory rounding conventions, such as `ROUND_HALF_UP`.

### Question 2: where inheritance was applied and where it was avoided
Inheritance was applied for the abstract base class `Tax` and the `TaxError` exception hierarchy. Subclasses share a polymorphic interface that satisfies the Liskov Substitution Principle.

Composition replaces inheritance for `Money`, which encapsulates `decimal.Decimal`. Encapsulation prevents non-monetary operations such as square roots and powers from executing on currency amounts. `PayrollPipeline` coordinates taxes through composition because it represents an organizational workflow.

---

## 8. Academic integrity and AI declaration

This project was developed with assistance from the AI coding assistant Antigravity (Google DeepMind).

Assistance covered:
- Drafting initial class structures and docstrings based on URA statutory documentation.
- Generating boundary test matrices and Hypothesis property strategies.
- Writing Matplotlib visualization scripts with labeled axes and formatting.

Engine calculations and object designs were checked against URA tax guides and verified using the automated test suite.

---

## 9. References

- *Income Tax Act* ([ULII Consolidated Legislation](https://media.ulii.org/media/legislation/112811/source_file/8eca548c5c6cd9f3/1997-11.pdf)).
- *Value Added Tax Act* ([ULII Consolidated Legislation](https://media.ulii.org/media/legislation/131171/source_file/de3dd76b1715d7a8/1996-8.pdf)). 
- *National Social Security Fund Act* ([ULII Consolidated Legislation](https://media.ulii.org/media/legislation/114231/source_file/686f9825c32ceb60/1985-8.pdf)).
- *Local Governments Act* ([ULII Act Archive](https://media.ulii.org/media/legislation/120257/source_file/2652f3b466854bcd/1997-5.pdf)).
- *Uganda Revenue Authority Act* ([ULII Consolidated Legislation](https://media.ulii.org/media/legislation/18776/source_file/c791ddbca546ff6a/1991-6.pdf)).
- *Uganda Revenue Authority Tax Guides and Circulars* ([URA Official Portal](https://ura.go.ug/en/tax-education/)).
