"""
Phase 6 Evidence Service package.
"""

from backend.app.services.evidence.independence import (
    compute_independent_source_count,
    get_independence_key,
    group_evidence_by_origin,
)
from backend.app.services.evidence.missing_evidence import compute_missing_evidence
from backend.app.services.evidence.providers import (
    ManualEvidenceProvider,
    RetrievedSourceItem,
    SourceLookupProvider,
    SourceLookupQuery,
    SourceLookupResult,
    SyntheticFallbackProvider,
    verification_service,
)
from backend.app.services.evidence.ssrf_guard import (
    SSRFSecurityError,
    SafeUrlValidationResult,
    check_safe_url_or_raise,
    validate_url_safety,
)
from backend.app.services.evidence.state_machine import (
    ALLOWED_EVIDENCE_TRANSITIONS,
    is_valid_evidence_transition,
    normalize_evidence_status,
    suggest_evidence_status,
    validate_evidence_transition,
)

__all__ = [
    "compute_independent_source_count",
    "get_independence_key",
    "group_evidence_by_origin",
    "compute_missing_evidence",
    "SourceLookupProvider",
    "ManualEvidenceProvider",
    "SyntheticFallbackProvider",
    "SourceLookupQuery",
    "SourceLookupResult",
    "RetrievedSourceItem",
    "verification_service",
    "validate_url_safety",
    "check_safe_url_or_raise",
    "SSRFSecurityError",
    "SafeUrlValidationResult",
    "ALLOWED_EVIDENCE_TRANSITIONS",
    "is_valid_evidence_transition",
    "validate_evidence_transition",
    "suggest_evidence_status",
    "normalize_evidence_status",
]
