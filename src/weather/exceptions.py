"""Custom exception hierarchy for the Weather Application.

Provides structured and domain-specific errors for geocoding, HTTP network issues,
upstream API failures, rate limiting, and schema parsing errors.
"""

from typing import Optional


class WeatherError(Exception):
    """Base exception for all weather application errors."""

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class NetworkError(WeatherError):
    """Raised when an HTTP connection fails or network unreachable."""
    pass


class NetworkTimeoutError(NetworkError):
    """Raised when an HTTP request exceeds the configured timeout duration."""
    pass


class RateLimitError(WeatherError):
    """Raised when upstream API rate limits are exceeded (HTTP 429)."""
    pass


class UpstreamServiceError(WeatherError):
    """Raised when an upstream weather service returns a 5xx server error."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[str] = None) -> None:
        super().__init__(message, details)
        self.status_code = status_code


class LocationNotFoundError(WeatherError):
    """Raised when geocoding returns no candidate locations for a given query."""
    pass


class AmbiguousLocationError(WeatherError):
    """Raised when multiple candidate locations match and automatic resolution is not allowed."""
    pass


class InvalidCoordinateError(WeatherError):
    """Raised when latitude or longitude fail geographical validity bounds."""
    pass


class ForecastParsingError(WeatherError):
    """Raised when an upstream payload cannot be parsed into forecast models."""
    pass

