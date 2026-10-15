"""Weather Forecast Package for OOP Assignment 2.

Exposes models, resilient HTTP client, services for Open-Meteo and MET Norway,
visualization utilities, and custom exceptions.
"""

from weather.client import DEFAULT_USER_AGENT, ResilientHTTPClient
from weather.exceptions import (
    AmbiguousLocationError,
    ForecastParsingError,
    InvalidCoordinateError,
    LocationNotFoundError,
    NetworkError,
    NetworkTimeoutError,
    RateLimitError,
    UpstreamServiceError,
    WeatherError,
)
from weather.models import DailyForecast, Location, WeatherForecastReport
from weather.services import (
    WMO_WEATHER_CODES,
    CompositeWeatherService,
    METNorwayForecastService,
    OpenMeteoForecastService,
    OpenMeteoGeocodingService,
    decode_wmo_code,
)
from weather.visualizer import WeatherVisualizer

__all__ = [
    # Models
    "Location",
    "DailyForecast",
    "WeatherForecastReport",
    # Client & Config
    "ResilientHTTPClient",
    "DEFAULT_USER_AGENT",
    # Services
    "OpenMeteoGeocodingService",
    "OpenMeteoForecastService",
    "METNorwayForecastService",
    "CompositeWeatherService",
    "decode_wmo_code",
    "WMO_WEATHER_CODES",
    # Visualizer
    "WeatherVisualizer",
    # Exceptions
    "WeatherError",
    "NetworkError",
    "NetworkTimeoutError",
    "RateLimitError",
    "UpstreamServiceError",
    "LocationNotFoundError",
    "AmbiguousLocationError",
    "InvalidCoordinateError",
    "ForecastParsingError",
]

