"""Weather API services for Open-Meteo geocoding/forecasting and MET Norway Locationforecast.

Implements:
- Geocoding with candidate ranking and ambiguity handling
- Open-Meteo forecast retrieval and WMO weather code decoding
- MET Norway Locationforecast 2.0 retrieval and aggregation
- Composite orchestration with automatic fallback and comparison
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from weather.client import ResilientHTTPClient
from weather.exceptions import (
    ForecastParsingError,
    LocationNotFoundError,
    WeatherError,
)
from weather.models import DailyForecast, Location, WeatherForecastReport

# Official WMO Weather interpretation codes (WW) per Open-Meteo documentation
WMO_WEATHER_CODES: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def decode_wmo_code(code: int) -> str:
    """Decode a numerical WMO weather code into a readable description."""
    return WMO_WEATHER_CODES.get(code, f"Unknown condition (code {code})")


class OpenMeteoGeocodingService:
    """Service to geocode city names into geographical coordinates via Open-Meteo."""

    ENDPOINT = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self, client: Optional[ResilientHTTPClient] = None) -> None:
        self.client = client or ResilientHTTPClient()

    def search_candidates(self, name: str, count: int = 5) -> List[Location]:
        """Query Open-Meteo for candidate locations matching the given name.

        Handles missing 'results' key gracefully when zero matches exist.
        """
        if not name or not name.strip():
            raise ValueError("City name must not be empty.")

        params = {
            "name": name.strip(),
            "count": max(1, count),
            "language": "en",
            "format": "json",
        }

        response = self.client.get(self.ENDPOINT, params=params)
        payload = response.json()

        # Open-Meteo omits the 'results' key when zero records match
        raw_results = payload.get("results")
        if not raw_results:
            return []

        candidates: List[Location] = []
        for item in raw_results:
            candidates.append(
                Location(
                    name=item.get("name", name),
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                    country=item.get("country"),
                    admin1=item.get("admin1"),
                    timezone=item.get("timezone"),
                    population=item.get("population"),
                    elevation=item.get("elevation"),
                )
            )
        return candidates

    def geocode(self, name: str, selection_index: int = 0) -> Location:
        """Geocode a city name and resolve candidates.

        Args:
            name: City or place name.
            selection_index: Zero-based index of candidate to select when multiple match.

        Returns:
            The selected Location model.

        Raises:
            LocationNotFoundError: When no candidate locations match.
            IndexError: If selection_index is out of range for candidates.
        """
        candidates = self.search_candidates(name, count=10)
        if not candidates:
            raise LocationNotFoundError(f"No location found matching '{name}'.")

        if selection_index < 0 or selection_index >= len(candidates):
            raise IndexError(
                f"Candidate index {selection_index} is out of range (found {len(candidates)} candidates)."
            )

        return candidates[selection_index]


class OpenMeteoForecastService:
    """Service to retrieve weather forecasts from Open-Meteo."""

    ENDPOINT = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, client: Optional[ResilientHTTPClient] = None) -> None:
        self.client = client or ResilientHTTPClient()

    def get_forecast(
        self,
        location: Location,
        days: int = 7,
        timezone: Optional[str] = None,
    ) -> WeatherForecastReport:
        """Fetch daily weather forecast for a location.

        Args:
            location: Validated Location model.
            days: Number of forecast days (1 to 16).
            timezone: Explicit timezone or 'auto'. Defaults to location.timezone or 'auto'.
        """
        tz = timezone or location.timezone or "auto"
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "wind_speed_10m_max",
                "weather_code",
            ],
            "timezone": tz,
            "forecast_days": max(1, min(days, 16)),
        }

        response = self.client.get(self.ENDPOINT, params=params)
        payload = response.json()
        return self.parse_forecast_payload(payload, location)

    @staticmethod
    def parse_forecast_payload(payload: Dict[str, Any], location: Location) -> WeatherForecastReport:
        """Parse raw Open-Meteo JSON payload into a WeatherForecastReport domain model."""
        daily = payload.get("daily")
        if not daily:
            raise ForecastParsingError("Open-Meteo response missing required 'daily' payload.")

        times = daily.get("time", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        wind = daily.get("wind_speed_10m_max", [])
        codes = daily.get("weather_code", [])

        length = len(times)
        if not (length == len(temp_max) == len(temp_min) == len(precip) == len(wind) == len(codes)):
            raise ForecastParsingError("Open-Meteo daily arrays have mismatched lengths.")

        records: List[DailyForecast] = []
        for i in range(length):
            w_code = int(codes[i]) if codes[i] is not None else 0
            records.append(
                DailyForecast(
                    date=str(times[i]),
                    temp_max=float(temp_max[i]),
                    temp_min=float(temp_min[i]),
                    precipitation_sum=float(precip[i]) if precip[i] is not None else 0.0,
                    wind_speed_max=float(wind[i]) if wind[i] is not None else 0.0,
                    weather_code=w_code,
                    weather_description=decode_wmo_code(w_code),
                )
            )

        return WeatherForecastReport(
            location=location,
            daily_records=records,
            provider="Open-Meteo",
        )


class METNorwayForecastService:
    """Service to retrieve weather forecasts from MET Norway Locationforecast 2.0.

    Requirements:
        - Must include valid contact information in the User-Agent header.
        - Transforms hourly/timeseries records into daily aggregated forecasts.
    """

    ENDPOINT = "https://api.met.no/weatherapi/locationforecast/2.0/compact"

    def __init__(self, client: Optional[ResilientHTTPClient] = None) -> None:
        self.client = client or ResilientHTTPClient()

    def get_forecast(self, location: Location, days: int = 7) -> WeatherForecastReport:
        """Fetch and aggregate daily forecast from MET Norway Locationforecast 2.0."""
        params = {
            "lat": round(location.latitude, 4),
            "lon": round(location.longitude, 4),
        }

        response = self.client.get(self.ENDPOINT, params=params)
        payload = response.json()
        return self.parse_forecast_payload(payload, location, days=days)

    @staticmethod
    def parse_forecast_payload(
        payload: Dict[str, Any], location: Location, days: int = 7
    ) -> WeatherForecastReport:
        """Parse MET Norway JSON payload and aggregate hourly timeseries into daily forecasts."""
        properties = payload.get("properties")
        if not properties or "timeseries" not in properties:
            raise ForecastParsingError("MET Norway payload missing 'properties.timeseries'.")

        timeseries = properties["timeseries"]
        if not timeseries:
            raise ForecastParsingError("MET Norway timeseries array is empty.")

        # Group data points by calendar date (YYYY-MM-DD)
        daily_temps: Dict[str, List[float]] = defaultdict(list)
        daily_precip: Dict[str, float] = defaultdict(float)
        daily_wind: Dict[str, List[float]] = defaultdict(list)
        daily_symbols: Dict[str, List[str]] = defaultdict(list)

        for entry in timeseries:
            time_iso = entry.get("time", "")
            date_str = time_iso.split("T")[0]
            data = entry.get("data", {})
            instant_details = data.get("instant", {}).get("details", {})

            if "air_temperature" in instant_details:
                daily_temps[date_str].append(float(instant_details["air_temperature"]))

            if "wind_speed" in instant_details:
                # MET Norway wind speed is in m/s; convert to km/h (1 m/s = 3.6 km/h)
                daily_wind[date_str].append(float(instant_details["wind_speed"]) * 3.6)

            # Check precipitation from next_1_hours or next_6_hours
            if "next_1_hours" in data:
                p = data["next_1_hours"].get("details", {}).get("precipitation_amount", 0.0)
                daily_precip[date_str] += float(p)
                sym = data["next_1_hours"].get("summary", {}).get("symbol_code")
                if sym:
                    daily_symbols[date_str].append(sym)
            elif "next_6_hours" in data:
                p = data["next_6_hours"].get("details", {}).get("precipitation_amount", 0.0)
                daily_precip[date_str] += float(p)
                sym = data["next_6_hours"].get("summary", {}).get("symbol_code")
                if sym:
                    daily_symbols[date_str].append(sym)

        # Build daily records
        sorted_dates = sorted(daily_temps.keys())[:days]
        records: List[DailyForecast] = []

        for date_str in sorted_dates:
            t_list = daily_temps[date_str]
            w_list = daily_wind[date_str]
            sym_list = daily_symbols[date_str]

            temp_max = max(t_list) if t_list else 0.0
            temp_min = min(t_list) if t_list else 0.0
            wind_max = max(w_list) if w_list else 0.0
            precip_total = daily_precip[date_str]
            most_frequent_sym = (
                max(set(sym_list), key=sym_list.count).replace("_", " ").capitalize()
                if sym_list
                else "Variable conditions"
            )

            records.append(
                DailyForecast(
                    date=date_str,
                    temp_max=round(temp_max, 1),
                    temp_min=round(temp_min, 1),
                    precipitation_sum=round(precip_total, 1),
                    wind_speed_max=round(wind_max, 1),
                    weather_code=0,
                    weather_description=most_frequent_sym,
                )
            )

        return WeatherForecastReport(
            location=location,
            daily_records=records,
            provider="MET Norway Locationforecast 2.0",
        )


class CompositeWeatherService:
    """Orchestrates multi-source weather forecasts with automated fallback and comparison."""

    def __init__(
        self,
        open_meteo_service: Optional[OpenMeteoForecastService] = None,
        met_norway_service: Optional[METNorwayForecastService] = None,
    ) -> None:
        self.open_meteo = open_meteo_service or OpenMeteoForecastService()
        self.met_norway = met_norway_service or METNorwayForecastService()

    def get_forecast_with_fallback(
        self,
        location: Location,
        days: int = 7,
        force_primary_failure: bool = False,
    ) -> Tuple[WeatherForecastReport, str]:
        """Attempt primary retrieval via Open-Meteo; fall back to MET Norway on failure.

        Args:
            location: Target location.
            days: Forecast duration.
            force_primary_failure: When True, simulates primary service failure to demonstrate fallback.

        Returns:
            Tuple of (WeatherForecastReport, provider_status_message).
        """
        if not force_primary_failure:
            try:
                report = self.open_meteo.get_forecast(location, days=days)
                return report, "Primary provider (Open-Meteo) succeeded."
            except WeatherError as err:
                fallback_reason = f"Primary provider failed ({err}). Triggering MET Norway fallback."
        else:
            fallback_reason = "Simulated primary failure. Triggering MET Norway fallback."

        # Execute fallback
        report = self.met_norway.get_forecast(location, days=days)
        return report, f"Fallback active: {fallback_reason}"

    def compare_forecasts(
        self, location: Location, days: int = 5
    ) -> pd.DataFrame:
        """Fetch forecasts from both providers and compile a side-by-side comparison DataFrame."""
        om_report = self.open_meteo.get_forecast(location, days=days)
        met_report = self.met_norway.get_forecast(location, days=days)

        om_df = om_report.to_dataframe().set_index("Date")
        met_df = met_report.to_dataframe().set_index("Date")

        # Inner join on common dates
        common_dates = sorted(list(set(om_df.index).intersection(set(met_df.index))))

        rows = []
        for d in common_dates:
            rows.append(
                {
                    "Date": d,
                    "Open-Meteo Max (°C)": om_df.loc[d, "Max Temp (°C)"],
                    "MET Norway Max (°C)": met_df.loc[d, "Max Temp (°C)"],
                    "Δ Max Temp (°C)": round(
                        om_df.loc[d, "Max Temp (°C)"] - met_df.loc[d, "Max Temp (°C)"], 2
                    ),
                    "Open-Meteo Precip (mm)": om_df.loc[d, "Precipitation (mm)"],
                    "MET Norway Precip (mm)": met_df.loc[d, "Precipitation (mm)"],
                    "Open-Meteo Condition": om_df.loc[d, "Condition"],
                    "MET Norway Condition": met_df.loc[d, "Condition"],
                }
            )

        return pd.DataFrame(rows)

