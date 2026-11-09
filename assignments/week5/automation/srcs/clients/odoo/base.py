"""Base Odoo API client with common HTTP functionality."""

import logging
import time
from typing import Any, Optional, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ODOOClient:
    """Base Odoo API client with retry logic and common HTTP patterns.

    Provides exponential backoff retry strategy and session management
    for reliable API communication with Odoo JSON-2 API.
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize Odoo base client.

        Args:
            base_url: Base URL for API calls (e.g., https://example.odoo.com/json/2)
            headers: Default headers to include in all requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for transient failures
        """
        self.base_url = base_url
        self.headers = headers or {}
        self.timeout = timeout
        self.max_retries = max_retries

        self.session = self._create_session(max_retries)

    def _create_session(self, max_retries: int) -> requests.Session:
        """Create requests session with retry strategy.

        P2 Issue #5 FIX: Separate read and write retry policies.

        Read operations (GET, HEAD, OPTIONS) are idempotent and safe to retry on transient failures.
        Write operations (POST, PUT, DELETE) are non-idempotent and must not be automatically retried.
        This prevents duplicate Odoo notes and other non-idempotent side effects on timeouts or 5xx.

        Args:
            max_retries: Maximum number of retries

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # SAFE: Retry policy for idempotent read operations
        # These operations are safe to retry on transient failures.
        # Retries use exponential backoff: 1, 2, 4 seconds between attempts.
        read_retry_strategy = Retry(
            total=max_retries,
            status=max_retries,
            connect=0,  # Never replay a possibly transmitted write after connection errors.
            read=0,
            other=0,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        # Mount read retry strategy for all requests
        # Since write operations have no retry-eligible methods, they will not be auto-retried
        adapter = HTTPAdapter(max_retries=read_retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> requests.Response:
        """Make HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (appended to base_url)
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            requests.RequestException: On network or HTTP errors
        """
        url = f"{self.base_url}{endpoint}"

        # Merge headers
        headers = {**self.headers, **kwargs.pop("headers", {})}

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {str(e)}")
            raise

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make GET request."""
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make POST request."""
        return self._request("POST", endpoint, **kwargs)

    def post_readonly(self, endpoint: str, **kwargs) -> requests.Response:
        """Retry only explicitly selected read-only JSON-2 POST operations.

        Never call this for message_post, write, or other remote mutations.
        """
        safe_methods = {"search", "read", "search_read", "search_count"}
        if endpoint.rstrip("/").split("/")[-1] not in safe_methods:
            raise ValueError(f"Not an approved read-only JSON-2 endpoint: {endpoint}")
        for attempt in range(self.max_retries + 1):
            try:
                return self.post(endpoint, **kwargs)
            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status not in (429, 500, 502, 503, 504) or attempt >= self.max_retries:
                    raise
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt >= self.max_retries:
                    raise
            # Small bounded exponential delay; no retries for non-read operations.
            time.sleep(min(0.1 * (2 ** attempt), 1.0))
        raise RuntimeError("unreachable")

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Make PUT request."""
        return self._request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make DELETE request."""
        return self._request("DELETE", endpoint, **kwargs)

    def close(self) -> None:
        """Close the session and clean up resources."""
        self.session.close()
        logger.debug("Client session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
