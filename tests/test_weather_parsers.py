"""Offline unit tests for weather domain models, parsers, and services.

Satisfies Part E requirement:
- At least 5 assert-based or pytest checks
- Executes purely offline using pre-saved sample JSON fixtures
- Validates data transformation, coordinate bounds, and error handling
"""

import json
from pathlib import Path
import pytest

from weather.exceptions import (
    ForecastParsingError,
    InvalidCoordinateError,
)
from weather.models import Location
from weather.services import (
    METNorwayForecastService,
    OpenMeteoForecastService,
    decode_wmo_code,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_location() -> Location:
    return Location(
        name="Mukono",
        latitude=0.3544,
        longitude=32.7553,
        country="Uganda",
        admin1="Central Region",
        timezone="Africa/Kampala",
    )


def test_1_wmo_code_decoding():
    """Check that WMO weather codes decode into descriptive strings."""
    assert decode_wmo_code(0) == "Clear sky"
    assert decode_wmo_code(61) == "Slight rain"
    assert decode_wmo_code(95) == "Thunderstorm"
    # Unknown code fallback
    assert "Unknown condition" in decode_wmo_code(999)


def test_2_location_validation_valid():
    """Check that Location instantiates cleanly with valid geographical coordinates."""
    loc = Location(name="Kampala", latitude=0.3136, longitude=32.5811, country="Uganda")
    assert loc.name == "Kampala"
    assert loc.display_name == "Kampala, Uganda"
    assert loc.coordinates_tuple == (0.3136, 32.5811)


def test_3_location_validation_invalid_coordinates():
    """Check that out-of-range latitude or longitude raises InvalidCoordinateError."""
    with pytest.raises(InvalidCoordinateError):
        Location(name="BadLat", latitude=95.0, longitude=32.0)

    with pytest.raises(InvalidCoordinateError):
        Location(name="BadLon", latitude=0.0, longitude=185.0)


def test_4_geocoding_fixture_parsing():
    """Check parsing of sample geocoding response with multiple candidates."""
    fixture_path = FIXTURES_DIR / "geocoding_success.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    assert len(results) == 2

    first = results[0]
    loc = Location(
        name=first["name"],
        latitude=first["latitude"],
        longitude=first["longitude"],
        country=first.get("country"),
        admin1=first.get("admin1"),
        timezone=first.get("timezone"),
    )
    assert loc.name == "Mukono"
    assert loc.country == "Uganda"
    assert loc.admin1 == "Central Region"
    assert loc.latitude == pytest.approx(0.3544)


def test_5_geocoding_empty_handling():
    """Check graceful parsing when geocoding response omits the 'results' key."""
    fixture_path = FIXTURES_DIR / "geocoding_empty.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Must safely return empty list without KeyError
    results = data.get("results", [])
    assert results == []


def test_6_open_meteo_forecast_parsing(sample_location):
    """Check parsing of Open-Meteo forecast JSON into domain models and DataFrame."""
    fixture_path = FIXTURES_DIR / "forecast_openmeteo.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    report = OpenMeteoForecastService.parse_forecast_payload(payload, sample_location)
    assert report.location.name == "Mukono"
    assert report.provider == "Open-Meteo"
    assert len(report.daily_records) == 7

    # Check first day metrics
    day0 = report.daily_records[0]
    assert day0.date == "2026-10-11"
    assert day0.temp_max == 27.4
    assert day0.temp_min == 17.8
    assert day0.precipitation_sum == 4.2
    assert day0.weather_description == "Slight rain showers"

    # Check DataFrame transformation
    df = report.to_dataframe()
    assert len(df) == 7
    expected_cols = [
        "Date",
        "Max Temp (°C)",
        "Min Temp (°C)",
        "Precipitation (mm)",
        "Max Wind Speed (km/h)",
        "WMO Code",
        "Condition",
    ]
    assert list(df.columns) == expected_cols

    # Check summary generation
    summary = report.summary_text()
    assert "Forecast for Mukono" in summary
    assert "Total Precipitation:" in summary


def test_7_open_meteo_malformed_payload_raises(sample_location):
    """Check that malformed daily payloads raise ForecastParsingError."""
    # Missing daily key
    with pytest.raises(ForecastParsingError):
        OpenMeteoForecastService.parse_forecast_payload({}, sample_location)

    # Mismatched array lengths
    bad_payload = {
        "daily": {
            "time": ["2026-10-11", "2026-10-12"],
            "temperature_2m_max": [25.0],  # only 1 element
            "temperature_2m_min": [18.0, 19.0],
            "precipitation_sum": [0.0, 1.0],
            "wind_speed_10m_max": [10.0, 12.0],
            "weather_code": [0, 1],
        }
    }
    with pytest.raises(ForecastParsingError):
        OpenMeteoForecastService.parse_forecast_payload(bad_payload, sample_location)


def test_8_met_norway_forecast_parsing(sample_location):
    """Check aggregation of MET Norway timeseries into daily forecast records."""
    fixture_path = FIXTURES_DIR / "forecast_metnorway.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    report = METNorwayForecastService.parse_forecast_payload(payload, sample_location, days=2)
    assert report.provider == "MET Norway Locationforecast 2.0"
    assert len(report.daily_records) == 2

    day1 = report.daily_records[0]
    assert day1.date == "2026-10-11"
    # Temps for 2026-10-11 were [18.0, 23.5, 27.0, 20.2] -> min 18.0, max 27.0
    assert day1.temp_max == 27.0
    assert day1.temp_min == 18.0
    # Precip for 2026-10-11 was [0.0, 1.2, 3.0, 0.0] -> sum 4.2
    assert day1.precipitation_sum == 4.2
    # Wind speeds were [2.5, 3.8, 4.2, 2.1] m/s -> max 4.2 * 3.6 = 15.12 km/h
    assert day1.wind_speed_max == pytest.approx(15.1, rel=1e-1)

