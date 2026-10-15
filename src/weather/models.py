"""Domain models for locations, daily forecasts, and weather forecast reports.

Includes type annotations, input validation, and DataFrame serialization.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
import pandas as pd

from weather.exceptions import InvalidCoordinateError


@dataclass(frozen=True)
class Location:
    """Represents a geographical location with validated coordinates.

    Attributes:
        name: Name of the city or locality.
        latitude: Latitude coordinate in decimal degrees [-90.0, 90.0].
        longitude: Longitude coordinate in decimal degrees [-180.0, 180.0].
        country: Country name or ISO code.
        admin1: First-level administrative division (e.g. state, province, district).
        timezone: Local timezone identifier (e.g. 'Africa/Kampala').
        population: Recorded population, if available.
        elevation: Elevation in meters above sea level, if available.
    """

    name: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    admin1: Optional[str] = None
    timezone: Optional[str] = None
    population: Optional[int] = None
    elevation: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate geographical latitude and longitude bounds."""
        if not (-90.0 <= self.latitude <= 90.0):
            raise InvalidCoordinateError(
                f"Latitude {self.latitude} is invalid; must be between -90.0 and 90.0 degrees."
            )
        if not (-180.0 <= self.longitude <= 180.0):
            raise InvalidCoordinateError(
                f"Longitude {self.longitude} is invalid; must be between -180.0 and 180.0 degrees."
            )

    @property
    def display_name(self) -> str:
        """Generate human-readable representation including administrative region and country."""
        parts = [self.name]
        if self.admin1:
            parts.append(self.admin1)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)

    @property
    def coordinates_tuple(self) -> tuple[float, float]:
        """Return (latitude, longitude) coordinate tuple."""
        return (self.latitude, self.longitude)

    def __str__(self) -> str:
        return f"{self.display_name} ({self.latitude:.4f}°, {self.longitude:.4f}°)"


@dataclass(frozen=True)
class DailyForecast:
    """Represents weather metrics for a single calendar day.

    Attributes:
        date: ISO 8601 date string (YYYY-MM-DD).
        temp_max: Maximum daily temperature in degrees Celsius (°C).
        temp_min: Minimum daily temperature in degrees Celsius (°C).
        precipitation_sum: Total daily precipitation in millimeters (mm).
        wind_speed_max: Maximum daily wind speed in kilometers per hour (km/h).
        weather_code: Numerical WMO weather interpretation code.
        weather_description: Human-readable decoded weather description.
    """

    date: str
    temp_max: float
    temp_min: float
    precipitation_sum: float
    wind_speed_max: float
    weather_code: int
    weather_description: str

    def __post_init__(self) -> None:
        """Sanity check metric values."""
        if self.precipitation_sum < 0.0:
            object.__setattr__(self, "precipitation_sum", 0.0)
        if self.wind_speed_max < 0.0:
            object.__setattr__(self, "wind_speed_max", 0.0)


@dataclass
class WeatherForecastReport:
    """Aggregates multi-day forecast records for a specific location.

    Attributes:
        location: The target location model.
        daily_records: Chronologically ordered list of daily forecast records.
        provider: Name of the meteorological data provider.
        retrieved_at: UTC timestamp when data was fetched.
    """

    location: Location
    daily_records: List[DailyForecast] = field(default_factory=list)
    provider: str = "Open-Meteo"
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dataframe(self) -> pd.DataFrame:
        """Convert daily forecast records into a clean pandas DataFrame with explicit units."""
        rows = []
        for record in self.daily_records:
            rows.append(
                {
                    "Date": record.date,
                    "Max Temp (°C)": record.temp_max,
                    "Min Temp (°C)": record.temp_min,
                    "Precipitation (mm)": record.precipitation_sum,
                    "Max Wind Speed (km/h)": record.wind_speed_max,
                    "WMO Code": record.weather_code,
                    "Condition": record.weather_description,
                }
            )
        df = pd.DataFrame(rows)
        return df

    def summary_text(self) -> str:
        """Generate a concise, analytical text summary of the forecast period."""
        if not self.daily_records:
            return f"No forecast data available for {self.location.display_name}."

        dates = [r.date for r in self.daily_records]
        max_temps = [r.temp_max for r in self.daily_records]
        min_temps = [r.temp_min for r in self.daily_records]
        precips = [r.precipitation_sum for r in self.daily_records]
        winds = [r.wind_speed_max for r in self.daily_records]

        overall_max = max(max_temps)
        overall_min = min(min_temps)
        total_precip = sum(precips)
        rain_days = sum(1 for p in precips if p > 0.1)
        max_wind = max(winds)

        summary = (
            f"Forecast for {self.location.display_name} ({dates[0]} to {dates[-1]})\n"
            f"• Source: {self.provider}\n"
            f"• Temperature Range: {overall_min:.1f}°C to {overall_max:.1f}°C\n"
            f"• Total Precipitation: {total_precip:.1f} mm across {rain_days} rainy day(s)\n"
            f"• Peak Wind Speed: {max_wind:.1f} km/h\n"
            f"• Primary Conditions: {', '.join(sorted(set(r.weather_description for r in self.daily_records)))}"
        )
        return summary

