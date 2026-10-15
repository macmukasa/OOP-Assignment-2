# OOP with Python - Assignment 2
MSCS & MSDS OOP with Python, Advent 2026

---

## 1. Project overview

This repository contains the completed solutions for Assignment 2 of the MSCS & MSDS Object-Oriented Programming (OOP) course. The assignment consists of two independent mini-projects:

- **Mini-Project 1: Resilient Weather API Client and Forecast Engine (`weather_api_project.ipynb`)**  
  An object-oriented forecasting library integrating Open-Meteo and MET Norway APIs. The package implements a resilient HTTP client with exponential backoff and retry policies, strict coordinate and payload validation, domain data models (`Location`, `DailyForecast`, `WeatherForecastReport`), and multi-panel Matplotlib visualizations.
- **Mini-Project 2: Uganda Statutory Tax Engine (`project2_uganda_tax_engine.ipynb`)**  
  An object-oriented tax calculator implementing statutory rules administered by the Uganda Revenue Authority (URA). The engine covers monthly progressive Pay As You Earn (PAYE), Employee and Employer NSSF contributions, Local Service Tax (LST), Value Added Tax (VAT) with input/output reconciliation, Corporate Income Tax (CIT) with loss relief carryforwards, Withholding Tax (WHT), and Individual Rental Income Tax.

### Statutory baselines and regulatory citations
- **Pay As You Earn (PAYE)**: *Income Tax Act, Cap 340, First Schedule*. Resident monthly progressive rates apply: Nil up to UGX 335,000; 20% on excess over 335,000 up to 410,000; 25% on excess over 410,000 up to 485,000; 30% on excess over 485,000 up to 10,000,000. An additional 10% surcharge applies on income exceeding UGX 10,000,000 per the *Income Tax (Amendment) Act 2012*. Non-residents pay 10% on their initial UGX 335,000 before proceeding to higher marginal brackets.
- **National Social Security Fund (NSSF)**: *NSSF Act, Cap 222* mandates an employee deduction of 5% and an employer matching contribution of 10% on gross cash remuneration.
- **Local Service Tax (LST)**: *Local Governments (Amendment) Act 2008* sets a statutory municipal deduction applied to employment income before PAYE determination.
- **Value Added Tax (VAT)**: *Value Added Tax Act, Cap 349* sets an 18% standard rate. Zero-rated supplies incur 0% VAT while retaining input tax recovery rights. Exempt supplies incur no output VAT and disallow input tax deduction under Section 28.
- **Corporate Income Tax (CIT)**: *Income Tax Act, Cap 340, Sections 22 and 38* set a 30% rate on resident corporate chargeable income, calculated as gross turnover less allowable deductions and assessed loss relief.
- **Withholding Tax (WHT)**: *Section 119* sets a 6% deduction on commercial goods supplies above UGX 1,000,000. *Section 119A* sets a 15% deduction on professional and consultancy fees.
- **Individual Rental Income Tax**: *Section 5(3) of the Income Tax (Amendment) Act 2022/2023* sets a flat 12% rate on gross rent exceeding UGX 235,000 monthly (UGX 2,820,000 annually), with zero deductions allowed for individuals.

---

## 2. Repository structure

```
.
├── Assignment_2_Advent_2026_MiniProjects.pdf  # Course project specification
├── README.md                                 # Consolidated project documentation
├── requirements.txt                          # Pip dependencies
├── environment.yml                           # Conda environment definition (oop2)
├── pytest.ini                                # Test runner configuration
├── weather_api_project.ipynb                 # Mini-Project 1 notebook
├── project2_uganda_tax_engine.ipynb          # Mini-Project 2 notebook
├── src/
│   ├── __init__.py
│   ├── weather/                              # Mini-Project 1 package
│   │   ├── __init__.py                       # Weather package exports
│   │   ├── client.py                         # Resilient HTTP client with retry and timeout logic
│   │   ├── exceptions.py                     # Weather exception hierarchy
│   │   ├── models.py                         # Location, DailyForecast, WeatherForecastReport
│   │   ├── services.py                       # Open-Meteo, MET Norway, and composite adapters
│   │   └── visualizer.py                     # Multi-panel Matplotlib forecast plots
│   └── tax_engine/                           # Mini-Project 2 package
│       ├── __init__.py                       # Tax engine package exports
│       ├── money.py                          # Immutable Money value object in UGX
│       ├── exceptions.py                     # TaxError exception hierarchy
│       ├── base.py                           # Abstract Tax class, TaxContext, TaxResult
│       ├── paye.py                           # Progressive PAYE engine
│       ├── payroll.py                        # Payroll pipeline (NSSF, LST, net pay, CTC)
│       ├── vat.py                            # VAT invoicing engine
│       ├── corporate.py                      # Corporate income tax, deductions, and loss relief
│       └── extensions.py                     # Withholding tax and rental tax
└── tests/
    ├── __init__.py
    ├── fixtures/                             # Offline JSON fixtures for weather tests
    │   ├── forecast_metnorway.json
    │   ├── forecast_openmeteo.json
    │   ├── geocoding_empty.json
    │   └── geocoding_success.json
    ├── test_weather_parsers.py               # Weather parser and validation tests (8 tests)
    ├── test_corporate.py                     # CIT assessment and loss carryforward tests
    ├── test_exceptions.py                    # Custom exceptions and input validation tests
    ├── test_extensions.py                    # WHT threshold and rental tax tests
    ├── test_hypothesis_properties.py         # Property-based testing with Hypothesis
    ├── test_money.py                         # Money immutability, operators, and float rejection
    ├── test_paye_boundaries.py               # Boundary tests at every statutory bracket
    ├── test_payroll.py                       # Payroll pipeline and deduction ordering
    └── test_vat.py                           # VAT invoices reconciliation and credit tests
```

---

## 3. Environment setup and execution

### Prerequisites
Python 3.13 or 3.14 with either `conda` or standard Python `venv`.

### Setting up the `oop2` conda environment
```powershell
# Create environment from specification
conda env create -f environment.yml

# Activate environment
conda activate oop2
```

### Alternative setup with pip
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Running automated tests
Run all 69 unit, boundary, and property-based tests across both mini-projects:
```powershell
pytest
```

Run tests for each mini-project independently:
```powershell
# Mini-Project 1 tests (8 weather tests)
pytest tests/test_weather_parsers.py

# Mini-Project 2 tests (61 tax engine tests)
pytest -k "not weather"
```

### Running the notebooks
Launch Jupyter:
```powershell
jupyter notebook
```
- Open `weather_api_project.ipynb` or `project2_uganda_tax_engine.ipynb`.
- Select the `oop2` kernel. Both notebooks execute top-to-bottom via **Kernel -> Restart & Run All**.

---

## 4. Software architecture and object-oriented design

### Mini-Project 1: Resilient weather forecasting architecture
- **Resilient HTTP Client (`ResilientHTTPClient`)**: Wraps `urllib.request` and `requests` with customizable retry backoff, exponential delays, jitter, timeout controls, and identifiable user-agent headers.
- **Data Models (`Location`, `DailyForecast`, `WeatherForecastReport`)**: Typed dataclasses with post-initialization bounds validation. `Location` strictly validates latitude ($[-90, 90]$) and longitude ($[-180, 180]$).
- **Polymorphic Forecast Services**: An abstract interface implemented by `OpenMeteoForecastService` and `METNorwayForecastService`. `CompositeWeatherService` queries multiple upstreams and aggregates responses.
- **Domain Exception Hierarchy**: Rooted in `WeatherError(Exception)`, with specialized subclasses: `NetworkError`, `NetworkTimeoutError`, `RateLimitError`, `UpstreamServiceError`, `LocationNotFoundError`, `AmbiguousLocationError`, `InvalidCoordinateError`, and `ForecastParsingError`.

### Mini-Project 2: Uganda tax engine architecture
- **Money Value Object (`Money`)**: Encapsulates `decimal.Decimal` in UGX with explicit `ROUND_HALF_UP` rounding. Rejects floating-point inputs and float arithmetic. Uses `__slots__` and frozen attribute setters to enforce immutability.
- **Abstract Tax Contract (`Tax`)**: Defines `calculate(self, ctx: TaxContext) -> TaxResult`. Concrete subclasses (`PAYETax`, `VATModule`, `CorporateIncomeTax`, `WithholdingTax`, `RentalIncomeTax`) adhere strictly to the Liskov Substitution Principle.
- **Composition over Inheritance**: `PayrollPipeline` coordinates deductions through composition rather than inheritance because a payroll processor is an orchestration workflow, not a tax.
- **Exception Hierarchy**: Rooted in `TaxError(Exception)`, with specific subclasses (`InvalidIncomeError`, `NoScheduleForDateError`, `CurrencyMismatchError`, `NegativeValueError`, `InvalidSupplyTypeError`, `TaxValidationError`).

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

### Mini-Project 1 test suite (`tests/test_weather_parsers.py`)
Evaluates parser resilience and domain models offline:
1. WMO weather code decoding to descriptive text and fallback handling.
2. Coordinate bounds validation for latitude and longitude.
3. Offline fixture parsing of Open-Meteo forecast JSON.
4. Offline fixture parsing of MET Norway location forecast JSON.
5. Error handling on malformed payloads and empty geocoding results.

### Mini-Project 2 test suite (`tests/test_*.py`)
- **Boundary tests (`tests/test_paye_boundaries.py`)**: Tests every statutory bracket edge (335,000 UGX, 410,000 UGX, 485,000 UGX, 10,000,000 UGX) for both residents and non-residents.
- **Property-based tests (`tests/test_hypothesis_properties.py`)**: Evaluates non-negativity, monotonicity, upper bound constraints, residency dominance, and take-home monotonicity across randomized incomes.
- **Value object tests (`tests/test_money.py`)**: Checks float rejection, arithmetic rounding, immutability, and currency mismatch safeguards.
- **Commercial tax tests (`tests/test_vat.py`, `tests/test_corporate.py`, `tests/test_extensions.py`)**: Validates VAT input/output credit reconciliation, CIT loss carryforwards, WHT thresholds, and rental tax exemptions.

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
- Drafting initial class structures and docstrings based on course specifications and URA statutory documentation.
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
- *Open-Meteo API Documentation* ([Open-Meteo Documentation](https://open-meteo.com/en/docs)).
- *MET Norway Weather API Documentation* ([MET Norway API](https://api.met.no/weatherapi/locationforecast/2.0/documentation)).
