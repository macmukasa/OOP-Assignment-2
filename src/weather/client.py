"""Resilient HTTP client with retry logic, exponential backoff, and custom error mapping.

Satisfies Part C requirement:
- Configurable timeout
- Automatic raise_for_status()
- Retries on connection errors and 5xx responses with exponential backoff and cap
- Raises clear domain-specific exceptions on terminal failure
- Enforces compliant User-Agent headers
"""

import os
import random
import time
from typing import Any, Dict, Optional
import requests

from weather.exceptions import (
    NetworkError,
    NetworkTimeoutError,
    RateLimitError,
    UpstreamServiceError,
    WeatherError,
)

DEFAULT_USER_AGENT = os.environ.get(
    "WEATHER_USER_AGENT",
    "WeatherAssignmentApp/1.0 (academic.project@mscs-oop.ac.ug; Python/3.11 requests/2.31)",
)


class ResilientHTTPClient:
    """A fault-tolerant HTTP client wrapping the requests library.

    Features:
        - Exponential backoff with random jitter.
        - Retry cap for transient network faults and 5xx server errors.
        - Configurable timeout per request or client-wide.
        - Custom domain exception translation.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        default_timeout: float = 8.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        session: Optional[requests.Session] = None,
    ) -> None:
        """Initialize the resilient client.

        Args:
            user_agent: Contact and application string sent in HTTP User-Agent.
            default_timeout: Default timeout in seconds for connect and read.
            max_retries: Maximum number of retry attempts on transient failures.
            backoff_factor: Base multiplier for exponential backoff.
            session: Optional custom requests.Session (useful for dependency injection in tests).
        """
        self.user_agent = user_agent
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = session or requests.Session()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> requests.Response:
        """Execute an HTTP GET request with retries, timeout enforcement, and error mapping.

        Args:
            url: The destination endpoint URL.
            params: Dictionary of query parameters.
            headers: Optional HTTP headers dictionary.
            timeout: Explicit timeout in seconds; overrides default_timeout if supplied.

        Returns:
            The successful requests.Response object.

        Raises:
            NetworkTimeoutError: When requests exceed timeout duration after all retries.
            NetworkError: When network connection fails after all retries.
            RateLimitError: When upstream server returns HTTP 429 Too Many Requests.
            UpstreamServiceError: When upstream server returns 5xx server errors after retries.
            WeatherError: For other non-transient HTTP client errors (e.g. 400 Bad Request).
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout

        req_headers = {"User-Agent": self.user_agent}
        if headers:
            req_headers.update(headers)

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=req_headers,
                    timeout=effective_timeout,
                )

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(
                        f"Upstream API rate limit exceeded for {url}.",
                        details=f"Retry-After header: {retry_after}" if retry_after else None,
                    )

                # Check for transient server errors (5xx)
                if 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        sleep_duration = self._calculate_backoff(attempt)
                        time.sleep(sleep_duration)
                        continue
                    else:
                        raise UpstreamServiceError(
                            f"Upstream server error (HTTP {response.status_code}) from {url}.",
                            status_code=response.status_code,
                            details=response.text[:200],
                        )

                # Non-transient client errors (4xx except 429) fail immediately without retrying
                response.raise_for_status()
                return response

            except requests.exceptions.Timeout as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    sleep_duration = self._calculate_backoff(attempt)
                    time.sleep(sleep_duration)
                else:
                    raise NetworkTimeoutError(
                        f"Request to {url} timed out after {effective_timeout}s over {self.max_retries + 1} attempts.",
                        details=str(exc),
                    ) from exc

            except requests.exceptions.ConnectionError as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    sleep_duration = self._calculate_backoff(attempt)
                    time.sleep(sleep_duration)
                else:
                    raise NetworkError(
                        f"Network connection failed when connecting to {url}.",
                        details=str(exc),
                    ) from exc

            except requests.exceptions.HTTPError as exc:
                # Catch 4xx status codes that were raised by raise_for_status()
                status = exc.response.status_code if exc.response is not None else None
                raise WeatherError(
                    f"HTTP client error {status} for {url}.",
                    details=exc.response.text[:200] if exc.response is not None else str(exc),
                ) from exc

        # Fallback if loop exits unexpectedly
        raise NetworkError(
            f"Exhausted {self.max_retries} retries connecting to {url}.",
            details=str(last_exception),
        )

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with additive uniform jitter."""
        base_delay = self.backoff_factor * (2 ** attempt)
        jitter = random.uniform(0.0, 0.25)
        return base_delay + jitter

