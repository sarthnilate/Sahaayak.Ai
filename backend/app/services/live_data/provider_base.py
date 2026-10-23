"""
Provider base interfaces, safe HTTP client, and source registry for Phase 6B Live Data.
Enforces:
- Strict host allowlist (https only, sachet.ndma.gov.in, api.imd.gov.in)
- SSRF prevention via ssrf_guard
- Timeouts (3s connect, 5s read)
- Max response size cap (2MB)
- ETag / conditional GET handling
- Freshness classification (fresh, stale, expired)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional
import httpx

from backend.app.services.evidence.ssrf_guard import validate_url_safety, SSRFSecurityError


ALLOWED_LIVE_HOSTS = {
    "sachet.ndma.gov.in",
    "api.imd.gov.in",
}

DEFAULT_MAX_BYTES = 2_000_000  # 2MB
DEFAULT_CONNECT_TIMEOUT = 3.0
DEFAULT_READ_TIMEOUT = 5.0
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes


class LiveDataSecurityError(Exception):
    """Raised when request violates live data security policies (host, ssrf, size)."""
    pass


class LiveDataFetchError(Exception):
    """Raised when fetching or parsing live source fails."""
    pass


@dataclass
class NormalizedAlert:
    source_id: str
    external_identifier: str
    headline: str
    event: str
    severity: str
    urgency: Optional[str]
    certainty: Optional[str]
    area_description: str
    language: str = "en"
    sender: Optional[str] = None
    sent_at: Optional[datetime] = None
    effective_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    source_url: Optional[str] = None
    centroid: Optional[str] = None
    raw_cap_xml: Optional[str] = None
    content_hash: str = ""
    is_synthetic: bool = False

    def __post_init__(self):
        if not self.content_hash:
            seed = f"{self.source_id}|{self.external_identifier}|{self.headline}|{self.severity}|{self.expires_at}"
            self.content_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()

    @property
    def freshness(self) -> str:
        now = datetime.now(timezone.utc)
        if self.expires_at:
            exp = self.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                return "expired"
        return "fresh"


@dataclass
class SourceStatusResult:
    source_id: str
    display_name: str
    status: str  # live_ok, live_empty, stale_cache, not_configured, blocked, error
    last_fetched_at: Optional[datetime] = None
    item_count: int = 0
    http_status: Optional[int] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


def validate_live_url(url: str) -> None:
    """Validate that the target URL conforms to strict host allowlist and SSRF guard."""
    from urllib.parse import urlparse
    if not url:
        raise LiveDataSecurityError("URL cannot be empty")
    
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() != "https":
        raise LiveDataSecurityError(f"Disallowed scheme '{parsed.scheme}'. Only HTTPS allowed.")
    
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_LIVE_HOSTS:
        raise LiveDataSecurityError(
            f"Host '{host}' is not in ALLOWED_LIVE_HOSTS ({', '.join(sorted(ALLOWED_LIVE_HOSTS))})"
        )
    
    # Run through full SSRF IP resolution guard
    validation = validate_url_safety(url)
    if not validation.is_safe:
        raise LiveDataSecurityError(f"SSRF validation blocked '{url}': {validation.error_message}")


class SafeLiveClient:
    """HTTP client wrapper with host validation, SSRF guard, timeouts, and byte limits."""

    def __init__(
        self,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ):
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_bytes = max_bytes

    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        validate_live_url(url)
        timeout = httpx.Timeout(self.read_timeout, connect=self.connect_timeout)
        headers = headers or {}
        headers.setdefault("User-Agent", "SahaayakAI-DisasterOps/1.0 (Emergency Response Coordinator)")
        
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.get(url, headers=headers)
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > self.max_bytes:
                raise LiveDataSecurityError(
                    f"Payload size {content_length} exceeds limit of {self.max_bytes} bytes"
                )
            if len(response.content) > self.max_bytes:
                raise LiveDataSecurityError(
                    f"Received payload size {len(response.content)} exceeds {self.max_bytes} bytes"
                )
            return response

    def post(self, url: str, json_data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        validate_live_url(url)
        timeout = httpx.Timeout(self.read_timeout, connect=self.connect_timeout)
        headers = headers or {}
        headers.setdefault("User-Agent", "SahaayakAI-DisasterOps/1.0 (Emergency Response Coordinator)")
        headers.setdefault("Content-Type", "application/json")
        
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.post(url, json=json_data, headers=headers)
            if len(response.content) > self.max_bytes:
                raise LiveDataSecurityError(
                    f"Received payload size {len(response.content)} exceeds {self.max_bytes} bytes"
                )
            return response


class BaseLiveDataProvider(ABC):
    """Abstract base provider for official live emergency data feeds."""

    @property
    @abstractmethod
    def source_id(self) -> str:
        """e.g. 'ndma_sachet', 'imd_api'"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @abstractmethod
    def fetch_alerts(self, force_refresh: bool = False) -> List[NormalizedAlert]:
        """Fetch and normalize alerts from the live source."""
        pass

    @abstractmethod
    def check_status(self) -> SourceStatusResult:
        """Return connectivity/operational status without throwing unhandled exceptions."""
        pass
