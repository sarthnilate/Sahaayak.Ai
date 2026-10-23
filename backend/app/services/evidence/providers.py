"""
Phase 6: Verification Provider Interface & Implementations.
Defines SourceLookupProvider with:
1. ManualEvidenceProvider (coordinator attachments)
2. SyntheticFallbackProvider (explicitly flagged, OFF by default, active only when LIVE_DATA_FALLBACK=labelled_demo)
3. Interface designed for seamless plugging of NDMA SACHET / IMD in Phase 6B without architectural changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.core.config import settings


@dataclass
class SourceLookupQuery:
    location_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    category: str = "waterlogging"
    temporal_window_hours: int = 24


@dataclass
class RetrievedSourceItem:
    source_name: str
    source_description: str
    source_url: Optional[str]  # Must be None for synthetic evidence
    source_timestamp: Optional[datetime]
    assessment: str  # supports, contradicts, neutral, contextual, unassessed
    evidence_type: str  # official_context, corroborating_report, contradictory, synthetic_test, manual_attachment
    excerpt: Optional[str] = None
    metadata_json: Dict[str, Any] = field(default_factory=dict)
    independence_group: Optional[str] = None
    is_simulated: bool = False


@dataclass
class SourceLookupResult:
    verification_available: bool
    provider_name: str
    items: List[RetrievedSourceItem] = field(default_factory=list)
    unavailable_reason: Optional[str] = None


class SourceLookupProvider(ABC):
    """Abstract interface for external source and telemetry lookup."""

    @abstractmethod
    def lookup(self, query: SourceLookupQuery) -> SourceLookupResult:
        """Queries the source provider for corroborating or contradictory context."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_live(self) -> bool:
        pass


class ManualEvidenceProvider(SourceLookupProvider):
    """Provider for coordinator-attached manual evidence."""

    @property
    def provider_name(self) -> str:
        return "Manual Coordinator Attachment"

    @property
    def is_live(self) -> bool:
        return False

    def lookup(self, query: SourceLookupQuery) -> SourceLookupResult:
        # Manual provider does not auto-fetch; items are created explicitly by coordinators
        return SourceLookupResult(
            verification_available=True,
            provider_name=self.provider_name,
            items=[],
        )


class SyntheticFallbackProvider(SourceLookupProvider):
    """
    Synthetic demo provider.
    STRICT SECURITY RULES:
    1. OFF by default.
    2. Active ONLY when LIVE_DATA_FALLBACK='labelled_demo'.
    3. Every synthetic evidence item carries is_simulated=True, evidence_type='synthetic_test',
       and source_url=None (NEVER fabricate URLs or fake live results).
    """

    @property
    def provider_name(self) -> str:
        return "Synthetic Demonstration Provider"

    @property
    def is_live(self) -> bool:
        return False

    def lookup(self, query: SourceLookupQuery) -> SourceLookupResult:
        if settings.LIVE_DATA_FALLBACK != "labelled_demo":
            return SourceLookupResult(
                verification_available=False,
                provider_name=self.provider_name,
                items=[],
                unavailable_reason="Synthetic fallback provider is disabled by system policy (LIVE_DATA_FALLBACK!=labelled_demo).",
            )

        now = datetime.now(timezone.utc)
        synthetic_item = RetrievedSourceItem(
            source_name="Municipal Flood Sensor Telemetry (SIMULATED)",
            source_description="Automated simulated ultrasonic level sensor indicating localized inundation.",
            source_url=None,  # Never fabricate URLs
            source_timestamp=now,
            assessment="supports",
            evidence_type="synthetic_test",
            excerpt="Sensor telemetry indicates water accumulation > 85cm in low-lying underpass.",
            metadata_json={"simulated_reading_cm": 85, "sensor_status": "simulated_active"},
            independence_group="simulated-telemetry-origin",
            is_simulated=True,
        )

        return SourceLookupResult(
            verification_available=True,
            provider_name=self.provider_name,
            items=[synthetic_item],
        )


class VerificationService:
    """Coordinates source lookup providers according to system policy."""

    def __init__(self):
        self.manual_provider = ManualEvidenceProvider()
        self.synthetic_provider = SyntheticFallbackProvider()

    def get_verification_availability(self) -> tuple[bool, Optional[str]]:
        """
        Checks whether independent verification from live feeds is available.
        In Phase 6, live external feeds (NDMA SACHET / IMD API) arrive in Phase 6B.
        If live sources are not enabled, returns verification_available=False
        unless explicitly configured with LIVE_DATA_FALLBACK=labelled_demo.
        """
        if settings.LIVE_SOURCES_ENABLED:
            return True, None

        if settings.LIVE_DATA_FALLBACK == "labelled_demo":
            return True, None

        return (
            False,
            "Independent verification is unavailable. No live official feeds are configured (NDMA SACHET / IMD API arrive in Phase 6B).",
        )

    def lookup_sources(self, query: SourceLookupQuery) -> SourceLookupResult:
        available, reason = self.get_verification_availability()
        if not available:
            return SourceLookupResult(
                verification_available=False,
                provider_name="None",
                items=[],
                unavailable_reason=reason,
            )

        # If synthetic demo fallback is explicitly enabled
        if settings.LIVE_DATA_FALLBACK == "labelled_demo":
            return self.synthetic_provider.lookup(query)

        return SourceLookupResult(
            verification_available=False,
            provider_name="None",
            items=[],
            unavailable_reason="No live providers configured in Phase 6.",
        )


verification_service = VerificationService()
